#!/usr/bin/env node
import { App } from 'aws-cdk-lib';
import { StudioStack } from '../lib/studio-stack.mjs';

const app = new App();
const ctx = (k) => app.node.tryGetContext(k);

new StudioStack(app, 'D20Studio', {
  // CloudFront certificates must live in us-east-1; the whole stack goes there.
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'us-east-1' },
  domainName: ctx('domainName'),
  hostedZoneId: ctx('hostedZoneId'),
  subdomain: ctx('subdomain'),
  secretParam: ctx('secretParam'),
  description: 'D20 Synth Workbench at studio.d20drums.com (static site + cloud save API)',
});
