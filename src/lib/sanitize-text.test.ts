import { describe, expect, it } from "vitest";
import { stripLeakedExportMarkup } from "./sanitize-text";

describe("stripLeakedExportMarkup", () => {
  it("returns text without <img unchanged, spacing included", () => {
    const text = "  two  spaces stay  ";
    expect(stripLeakedExportMarkup(text)).toBe(text);
  });

  it("removes a leaked ReportLab image tag and tidies the spacing", () => {
    expect(stripLeakedExportMarkup('Before <img src="/x.png" width="10"/> after')).toBe("Before after");
  });

  it("removes several tags, case-insensitively", () => {
    expect(stripLeakedExportMarkup('<IMG src="a.png"> one <img src="b.png" /> two')).toBe("one two");
  });

  it("keeps an <img without src (not the ReportLab shape)", () => {
    expect(stripLeakedExportMarkup("a <img> b")).toBe("a <img> b");
  });
});
