import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";

const MAX_CALLS = 8;
const MAX_CONTEXT = 128 * 1024;
const MAX_MESSAGE_SNAPSHOT = 512 * 1024;
function strings(value, found = []) {
  if (typeof value === "string") found.push(value);
  else if (Array.isArray(value)) value.forEach((item) => strings(item, found));
  else if (value && typeof value === "object") Object.values(value).forEach((item) => strings(item, found));
  return found;
}

function representation(leaves, payload) {
  if (leaves.some((leaf) => leaf.includes(payload))) return { kind: "raw", text: payload };
  const escaped = JSON.stringify(payload).slice(1, -1);
  if (leaves.some((leaf) => leaf.includes(escaped))) return { kind: "json_escaped", text: escaped };
  return null;
}

export const Trace = async () => {
  return {
    "experimental.chat.messages.transform": async (input, output) => {
      const runDir = process.env.SKOPOS_PILOT_RUN_DIR;
      if (!runDir) throw new Error("pilot_run_not_configured");
      const tracePath = runDir + "/call-trace.jsonl";
      const deliveryPath = runDir && runDir + "/deliveries.jsonl";
      const deliveries = deliveryPath && existsSync(deliveryPath)
        ? readFileSync(deliveryPath, "utf8").trim().split("\n").filter(Boolean).map((line) => JSON.parse(line))
        : [];
      const leaves = strings(output.messages);
      const matched = deliveries.map((item) => ({ item,
        effective: representation(leaves, item.payload),
      })).filter((match) => match.effective);
      const previous = existsSync(tracePath)
        ? readFileSync(tracePath, "utf8").trim().split("\n").filter(Boolean).map((line) => JSON.parse(line))
        : [];
      const callIndex = previous.length + 1;
      const deliveredBytes = matched.reduce((sum, match) => sum + Buffer.byteLength(match.effective.text, "utf8"), 0);
      const cumulativeBytes = previous.reduce((sum, item) => sum + item.delivered_bytes, 0) + deliveredBytes;
      const violation = callIndex > MAX_CALLS ? "model_call_budget_exceeded"
        : cumulativeBytes > MAX_CONTEXT ? "context_budget_exceeded" : null;
      const serialized = JSON.stringify(output.messages);
      const capture = process.env.SKOPOS_PILOT_MESSAGE_CAPTURE === "synthetic_bounded_v1";
      const messageBytes = Buffer.from(serialized, "utf8");
      const snapshotViolation = capture && messageBytes.length > MAX_MESSAGE_SNAPSHOT
        ? "message_snapshot_limit_exceeded" : null;
      const messagesRef = capture && !snapshotViolation
        ? `messages/call-${String(callIndex).padStart(3, "0")}.json` : null;
      if (messagesRef) {
        mkdirSync(runDir + "/messages", { recursive: true, mode: 0o700 });
        writeFileSync(runDir + "/" + messagesRef, messageBytes,
          { flag: "wx", mode: 0o600 });
      }
      appendFileSync(tracePath, JSON.stringify({
        type: "messages_transform",
        call_index: callIndex,
        input_keys: Object.keys(input ?? {}).sort(),
        message_count: output.messages?.length ?? null,
        matched_deliveries: matched.map(({ item, effective }) => ({
          request_id: item.request_id,
          invocation_id: item.invocation_id,
          context_sha256: item.context_sha256,
          session_id: item.session_id,
          representation: effective.kind,
          effective_sha256: createHash("sha256").update(effective.text).digest("hex"),
          effective_bytes: Buffer.byteLength(effective.text, "utf8"),
        })),
        delivered_bytes: deliveredBytes,
        cumulative_bytes: cumulativeBytes,
        violation: violation ?? snapshotViolation,
        messages_sha256: createHash("sha256").update(serialized).digest("hex"),
        messages_ref: messagesRef,
        messages_capture: capture ? "synthetic_bounded_v1" : "none",
      }) + "\n");
      if (violation || snapshotViolation) throw new Error(violation ?? snapshotViolation);
    },
  };
};
