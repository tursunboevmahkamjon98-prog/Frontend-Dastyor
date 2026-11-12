import { describe, expect, it } from "vitest";
import { MIN_PASSWORD_LENGTH, isStrongPassword } from "./password";

describe("isStrongPassword", () => {
  it("accepts a password of exactly the minimum length", () => {
    expect(isStrongPassword("a".repeat(MIN_PASSWORD_LENGTH))).toBe(true);
  });

  it("rejects a password one character short", () => {
    expect(isStrongPassword("a".repeat(MIN_PASSWORD_LENGTH - 1))).toBe(false);
  });

  it("rejects an empty password", () => {
    expect(isStrongPassword("")).toBe(false);
  });
});
