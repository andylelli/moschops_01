import { buildApp } from './src/app';
import { prismaClient } from './src/services/prisma';
import fs from 'node:fs';
import path from 'node:path';

async function main() {
  const app = buildApp();
  
  app.get('/model-version', async () => {
    const version = await prismaClient().modelVersion.findFirst({
      orderBy: { createdAt: 'desc' },
    });
    return version;
  });

  try {
    await app.ready();
    const response = await app.inject({
      method: 'GET',
      url: '/model-version',
    });

    const outputDir = path.resolve('C:/moschops_01/docs/07-temp/evidence');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const outputPath = path.join(outputDir, 'model_version_probe_2026-05-21.json');
    const body = JSON.parse(response.body);
    fs.writeFileSync(outputPath, JSON.stringify(body, null, 2));

    process.stdout.write(`Status Code: ${response.statusCode}\n`);
    process.stdout.write(`modelVersion: ${body?.modelVersion ?? 'null'}\n`);
  } catch (error) {
    console.error(error);
    process.exit(1);
  } finally {
    await app.close();
  }
}

main();
