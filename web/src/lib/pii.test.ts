import { describe, expect, it } from "vitest";

import { describeIdentifiers, findIdentifiers, isMedicareNumber, isTfn } from "./pii";

// Mirrors tests/test_pii.py so the browser and API checks agree.
const VALID_TFN = "123456782";
const VALID_MEDICARE = "2123456701";

describe("checksums", () => {
  it("validates TFNs and Medicare numbers", () => {
    expect(isTfn(VALID_TFN)).toBe(true);
    expect(isTfn("123456789")).toBe(false);
    expect(isMedicareNumber(VALID_MEDICARE)).toBe(true);
    expect(isMedicareNumber("2123456791")).toBe(false);
  });
});

describe("findIdentifiers", () => {
  it.each([
    ["my TFN is 123 456 782, why no refund?", ["tax file number"]],
    [`medicare card ${VALID_MEDICARE} expired`, ["Medicare number"]],
    ["passport PA1234567 renewal", ["passport number"]],
    ["email me at jane.citizen@example.com", ["email address"]],
    ["call me on 0412 345 678", ["phone number"]],
    ["my landline is (02) 9876 5432", ["phone number"]],
    ["ring +61 412 345 678 please", ["phone number"]],
  ])("finds identifiers in %s", (text, expected) => {
    expect(findIdentifiers(text)).toEqual(expected);
  });

  it.each([
    "is $45,000 taxed at 15% for 2025-26?",
    "is 13 28 61 the right ATO number?",
    "should I call 1800 020 504 about my visa",
    "how much HECS do I repay on 123456789 dollars",
    "what is the DASP tax rate",
  ])("leaves ordinary numbers alone: %s", (text) => {
    expect(findIdentifiers(text)).toEqual([]);
  });
});

describe("describeIdentifiers", () => {
  it("joins kinds into readable text", () => {
    expect(describeIdentifiers(["tax file number"])).toBe("a tax file number");
    expect(describeIdentifiers(["email address", "phone number"])).toBe(
      "an email address and a phone number",
    );
  });
});
