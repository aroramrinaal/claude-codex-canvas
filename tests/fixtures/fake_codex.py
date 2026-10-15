"""Offline subprocess double. Never imports or invokes the real Codex CLI."""
import json
import os
import sys
import time
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

args = sys.argv[1:]
mode = os.environ.get("FAKE_CODEX_MODE", "success")
if args == ["--version"]:
    print("codex-cli fake-test")
elif args == ["exec", "--help"]:
    print("--json --ephemeral --skip-git-repo-check --sandbox --model")
elif args == ["features", "list"]:
    print("image_generation stable " + ("false" if mode == "disabled" else "true"))
elif args == ["login", "status"]:
    print("Logged in using " + ("API key" if mode == "api-auth" else "ChatGPT"))
else:
    assert sys.stdin.read() == "", "stdin must be closed"
    assert "OPENAI_API_KEY" not in os.environ and "CODEX_API_KEY" not in os.environ
    assert args[:4] == ["-a", "never", "exec", "--json"]
    assert args[args.index("-s") + 1] == "read-only"
    handoff = args[-1]
    payload = json.loads(handoff.split("Image tool arguments:\n", 1)[1])
    for reference in payload.get("referenced_image_paths", []):
        with Image.open(reference) as image:
            image.verify()
    thread = str(uuid.uuid4())
    print(json.dumps({"type": "thread.started", "thread_id": thread}), flush=True)
    if mode == "timeout":
        time.sleep(30)
    root = Path(os.environ["CODEX_HOME"]) / "generated_images" / thread
    if mode not in ("missing", "partial", "failure", "exit-failure"):
        root.mkdir(parents=True)
        for i in range(2 if mode == "multiple" else 1):
            output = root / f"exec-{i}.png"
            image = Image.new("RGBA", (48, 32), "white" if mode == "opaque" else (0, 0, 0, 0))
            if mode != "blank":
                ImageDraw.Draw(image).rectangle((8, 8, 35, 23), fill="#f2ce43")
            image.save(output)
            if mode == "corrupt":
                output.write_bytes(b"not a png")
            if mode == "stale":
                os.utime(output, (1, 1))
            if mode == "symlink":
                original = root / "source.dat"
                output.rename(original)
                output.symlink_to(original)
    if mode == "failure":
        print(json.dumps({"type": "turn.failed", "error": {"message": "quota exhausted"}}))
    elif mode == "bad-json":
        print("not JSON")
    elif mode != "partial":
        print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "DONE"}}))
        print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10}}))
    if mode == "exit-failure":
        sys.exit(2)
