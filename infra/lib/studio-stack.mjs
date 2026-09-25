import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  Stack, Duration, RemovalPolicy, CfnOutput,
  aws_s3 as s3,
  aws_s3_deployment as s3deploy,
  aws_cloudfront as cf,
  aws_cloudfront_origins as origins,
  aws_certificatemanager as acm,
  aws_route53 as r53,
  aws_route53_targets as targets,
  aws_dynamodb as ddb,
  aws_lambda as lambda,
  aws_logs as logs,
  aws_iam as iam,
  aws_ssm as ssm,
  aws_apigatewayv2 as apigw,
  aws_apigatewayv2_integrations as integrations,
} from 'aws-cdk-lib';

const here = path.dirname(fileURLToPath(import.meta.url));
const BUILD = path.resolve(here, '..', '..', 'build');

export class StudioStack extends Stack {
  constructor(scope, id, props) {
    super(scope, id, props);
    const { domainName, hostedZoneId, subdomain, secretParam } = props;
    const fqdn = `${subdomain}.${domainName}`;

    // ---- DNS + certificate ----
    const zone = r53.HostedZone.fromHostedZoneAttributes(this, 'Zone', { hostedZoneId, zoneName: domainName });
    const cert = new acm.Certificate(this, 'Cert', {
      domainName: fqdn,
      validation: acm.CertificateValidation.fromDns(zone),
    });

    // ---- storage ----
    const table = new ddb.Table(this, 'Table', {
      partitionKey: { name: 'pk', type: ddb.AttributeType.STRING },
      sortKey: { name: 'sk', type: ddb.AttributeType.STRING },
      billingMode: ddb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    const dataBucket = new s3.Bucket(this, 'DataBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      versioned: true,
      lifecycleRules: [{ noncurrentVersionExpiration: Duration.days(30) }],
      removalPolicy: RemovalPolicy.RETAIN,
    });

    const siteBucket = new s3.Bucket(this, 'SiteBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // ---- API ----
    const secret = ssm.StringParameter.fromSecureStringParameterAttributes(this, 'Secret', {
      parameterName: secretParam,
    });

    const fn = new lambda.Function(this, 'ApiFn', {
      runtime: lambda.Runtime.NODEJS_22_X,
      architecture: lambda.Architecture.ARM_64,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(BUILD, 'lambda')),
      memorySize: 512,
      timeout: Duration.seconds(15),
      environment: {
        NODE_ENV: 'production',
        NODE_OPTIONS: '--enable-source-maps',
        TABLE: table.tableName,
        DATA_BUCKET: dataBucket.bucketName,
        SECRET_PARAM: secretParam,
        MAX_PROJECTS_PER_USER: '200',
      },
      logGroup: new logs.LogGroup(this, 'ApiLogs', {
        retention: logs.RetentionDays.ONE_MONTH,
        removalPolicy: RemovalPolicy.DESTROY,
      }),
    });
    table.grantReadWriteData(fn);
    dataBucket.grantReadWrite(fn);
    secret.grantRead(fn);
    fn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['kms:Decrypt'],
      resources: ['*'],
      conditions: { StringEquals: { 'kms:ViaService': `ssm.${this.region}.amazonaws.com` } },
    }));

    const api = new apigw.HttpApi(this, 'HttpApi', {
      description: `${fqdn} API`,
      defaultIntegration: new integrations.HttpLambdaIntegration('ApiInt', fn),
    });
    // Coarse abuse/cost guard on the whole API.
    const stage = api.defaultStage.node.defaultChild;
    stage.defaultRouteSettings = { throttlingBurstLimit: 50, throttlingRateLimit: 25 };

    // ---- CDN ----
    // Serves /workbench and any other directory path from its index.html.
    const indexRewrite = new cf.Function(this, 'IndexRewrite', {
      runtime: cf.FunctionRuntime.JS_2_0,
      code: cf.FunctionCode.fromInline(`
function handler(event) {
  var r = event.request;
  if (r.uri.endsWith('/')) r.uri += 'index.html';
  else if (r.uri === '/workbench') r.uri = '/workbench/index.html';
  return r;
}`),
    });

    const dist = new cf.Distribution(this, 'Cdn', {
      comment: fqdn,
      domainNames: [fqdn],
      certificate: cert,
      defaultRootObject: 'index.html',
      priceClass: cf.PriceClass.PRICE_CLASS_100,
      httpVersion: cf.HttpVersion.HTTP2_AND_3,
      minimumProtocolVersion: cf.SecurityPolicyProtocol.TLS_V1_2_2021,
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(siteBucket),
        viewerProtocolPolicy: cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cf.CachePolicy.CACHING_OPTIMIZED,
        responseHeadersPolicy: cf.ResponseHeadersPolicy.SECURITY_HEADERS,
        compress: true,
        functionAssociations: [{ function: indexRewrite, eventType: cf.FunctionEventType.VIEWER_REQUEST }],
      },
      additionalBehaviors: {
        '/api/*': {
          origin: new origins.HttpOrigin(`${api.apiId}.execute-api.${this.region}.amazonaws.com`, {
            protocolPolicy: cf.OriginProtocolPolicy.HTTPS_ONLY,
          }),
          viewerProtocolPolicy: cf.ViewerProtocolPolicy.HTTPS_ONLY,
          allowedMethods: cf.AllowedMethods.ALLOW_ALL,
          cachePolicy: cf.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cf.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
          compress: true,
        },
      },
    });

    new s3deploy.BucketDeployment(this, 'DeploySite', {
      sources: [s3deploy.Source.asset(path.join(BUILD, 'site'))],
      destinationBucket: siteBucket,
      distribution: dist,
      distributionPaths: ['/*'],
      prune: true,
      memoryLimit: 512,
    });

    new r53.ARecord(this, 'AliasA', {
      zone, recordName: subdomain, target: r53.RecordTarget.fromAlias(new targets.CloudFrontTarget(dist)),
    });
    new r53.AaaaRecord(this, 'AliasAAAA', {
      zone, recordName: subdomain, target: r53.RecordTarget.fromAlias(new targets.CloudFrontTarget(dist)),
    });

    new CfnOutput(this, 'Url', { value: `https://${fqdn}` });
    new CfnOutput(this, 'DistributionId', { value: dist.distributionId });
    new CfnOutput(this, 'ApiEndpoint', { value: api.apiEndpoint });
    new CfnOutput(this, 'TableName', { value: table.tableName });
    new CfnOutput(this, 'DataBucketName', { value: dataBucket.bucketName });
  }
}
