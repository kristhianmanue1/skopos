import { tool } from "@opencode-ai/plugin";
import { spawn } from "node:child_process";
import { appendFileSync } from "node:fs";
import { createHash, randomUUID } from "node:crypto";

function invoke(value, context) {
  return new Promise((resolve, reject) => {
    const runDir = process.env.SKOPOS_PILOT_RUN_DIR;
    const python = process.env.SKOPOS_PILOT_PYTHON;
    const adapter = process.env.SKOPOS_PILOT_ADAPTER;
    if (!runDir || !python || !adapter) return reject(new Error("pilot_run_not_configured"));
    const child = spawn(python, [adapter, runDir], {
      stdio: ["pipe", "pipe", "pipe"],
      env: process.env,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (data) => { stdout += data; });
    child.stderr.on("data", (data) => { stderr += data; });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) return reject(new Error(stderr.trim().slice(0, 120)));
      const payload = stdout.trimEnd();
      const result = JSON.parse(payload);
      appendFileSync(runDir + "/deliveries.jsonl", JSON.stringify({
        invocation_id: randomUUID(),
        request_id: result.request_id,
        session_id: context?.sessionID ?? null,
        message_id: context?.messageID ?? null,
        purpose: "tool_result",
        context_sha256: createHash("sha256").update(Buffer.from(payload, "utf8")).digest("hex"),
        delivered_bytes: Buffer.byteLength(payload, "utf8"),
        payload,
      }) + "\n");
      resolve(process.env.SKOPOS_PILOT_OMIT_CONTEXT === "1"
        ? "Contexto omitido deliberadamente para control negativo."
        : payload);
    });
    child.stdin.end(JSON.stringify(value));
  });
}

export const search = tool({
  description: "Busca literalmente en fuentes verificadas del proyecto de esta tarea. Devuelve identidades, exclusiones y fuentes indisponibles; una búsqueda vacía no demuestra inexistencia global.",
  args: { term: tool.schema.string().describe("Subcadena literal que buscar") },
  async execute(args, context) { return await invoke({ operation: "search", term: args.term }, context); },
});

export const fetch = tool({
  description: "Lee una proyección textual de una revisión explícita usando los selectores e identidad del catálogo o de un resultado. Conserva fuente, revisión y hash.",
  args: {
    source_id: tool.schema.string(),
    source_revision: tool.schema.number().int(),
    source_sha256: tool.schema.string(),
    text_id: tool.schema.string(),
  },
  async execute(args, context) { return await invoke({ operation: "fetch", ...args }, context); },
});
