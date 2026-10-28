import { execSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

export default function globalSetup() {
  // Deterministic starting point: reload the synthetic demo organization.
  execSync("uv run python -m app.seed", { cwd: path.resolve(here, "../../backend"), stdio: "inherit" });
}
