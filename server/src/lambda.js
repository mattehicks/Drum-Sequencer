// AWS Lambda entrypoint (API Gateway HTTP API, payload v2) behind CloudFront /api/*.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import serverless from 'serverless-http';
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';
import { createApp } from './app.js';
import { awsStore } from './store/aws.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const region = process.env.AWS_REGION;

let handlerPromise;
async function init() {
  const ssm = new SSMClient({ region });
  const p = await ssm.send(new GetParameterCommand({ Name: process.env.SECRET_PARAM, WithDecryption: true }));
  const app = createApp({
    store: awsStore({ table: process.env.TABLE, bucket: process.env.DATA_BUCKET, region }),
    secret: p.Parameter.Value,
    prod: true,
    maxProjects: Number(process.env.MAX_PROJECTS_PER_USER || 200),
    maxBodyBytes: 5 * 1024 * 1024,   // Lambda sync payload limit is 6 MB
    kitDir: path.join(here, 'instrument-library'),
  });
  return serverless(app);
}

export async function handler(event, context) {
  handlerPromise ||= init().catch((e) => { handlerPromise = null; throw e; });
  const h = await handlerPromise;
  return h(event, context);
}
