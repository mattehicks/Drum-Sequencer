// Creates the session-signing secret as an SSM SecureString if it doesn't exist yet.
// (CloudFormation can't create SecureString parameters, so this runs before cdk deploy.)
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';

const cfg = JSON.parse(fs.readFileSync(new URL('../cdk.json', import.meta.url), 'utf8')).context;
const name = cfg.secretParam;
const region = 'us-east-1';
const aws = (...args) => execFileSync('aws', [...args, '--region', region, '--output', 'json'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });

try {
  aws('ssm', 'get-parameter', '--name', name);
  console.log(`secret ${name}: exists`);
} catch (e) {
  if (!String(e.stderr).includes('ParameterNotFound')) throw e;
  aws('ssm', 'put-parameter', '--name', name, '--type', 'SecureString',
      '--value', crypto.randomBytes(32).toString('hex'),
      '--description', 'Session cookie signing key for studio.d20drums.com');
  console.log(`secret ${name}: created`);
}
