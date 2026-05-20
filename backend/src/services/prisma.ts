import { PrismaClient } from "@prisma/client";

let prismaSingleton: PrismaClient | null = null;

export function prismaClient(): PrismaClient {
  if (!prismaSingleton) {
    prismaSingleton = new PrismaClient();
  }
  return prismaSingleton;
}
