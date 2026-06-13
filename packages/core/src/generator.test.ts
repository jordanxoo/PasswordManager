import { describe, it, expect } from "vitest";
import {
  generatePassword,
  alphabetSize,
  entropyBits,
  strength,
  MIN_LENGTH,
  MAX_LENGTH,
} from "./generator";

describe("generatePassword", () => {
  it("honours the requested length", () => {
    for (const len of [8, 16, 20, 64]) {
      expect(generatePassword({ length: len })).toHaveLength(len);
    }
  });

  it("clamps length to the supported range", () => {
    expect(generatePassword({ length: 1 })).toHaveLength(MIN_LENGTH);
    expect(generatePassword({ length: 9999 })).toHaveLength(MAX_LENGTH);
  });

  it("guarantees at least one char from every enabled group", () => {
    // numbers + symbols only — a digit and a symbol must both appear.
    for (let i = 0; i < 200; i++) {
      const pw = generatePassword({
        length: 8,
        uppercase: false,
        lowercase: false,
        numbers: true,
        symbols: true,
      });
      expect(/[0-9]/.test(pw)).toBe(true);
      expect(/[^0-9]/.test(pw)).toBe(true); // a symbol
    }
  });

  it("only uses lowercase when that's the only group", () => {
    const pw = generatePassword({
      length: 40,
      uppercase: false,
      lowercase: true,
      numbers: false,
      symbols: false,
    });
    expect(/^[a-z]+$/.test(pw)).toBe(true);
  });

  it("excludes ambiguous characters when asked", () => {
    for (let i = 0; i < 200; i++) {
      const pw = generatePassword({ length: 32, excludeAmbiguous: true });
      expect(/[0O1lI]/.test(pw)).toBe(false);
    }
  });

  it("throws when no character set is enabled", () => {
    expect(() =>
      generatePassword({
        uppercase: false,
        lowercase: false,
        numbers: false,
        symbols: false,
      }),
    ).toThrow();
  });

  it("is overwhelmingly unlikely to repeat", () => {
    const a = generatePassword({ length: 24 });
    const b = generatePassword({ length: 24 });
    expect(a).not.toBe(b);
  });
});

describe("alphabetSize / entropyBits / strength", () => {
  it("sums enabled groups", () => {
    expect(alphabetSize({ uppercase: true, lowercase: true, numbers: true, symbols: true }))
      .toBe(26 + 26 + 10 + 26);
    expect(alphabetSize({ uppercase: false, lowercase: true, numbers: true, symbols: false }))
      .toBe(26 + 10);
  });

  it("shrinks the alphabet when ambiguous chars are excluded", () => {
    const full = alphabetSize({ excludeAmbiguous: false });
    const trimmed = alphabetSize({ excludeAmbiguous: true });
    expect(trimmed).toBeLessThan(full);
  });

  it("computes log2-based entropy", () => {
    expect(entropyBits(10, 64)).toBe(60); // 10 * 6
    expect(entropyBits(0, 64)).toBe(0);
    expect(entropyBits(10, 1)).toBe(0);
  });

  it("buckets strength by entropy", () => {
    expect(strength(20)).toBe("weak");
    expect(strength(50)).toBe("fair");
    expect(strength(80)).toBe("strong");
    expect(strength(128)).toBe("excellent");
  });
});
