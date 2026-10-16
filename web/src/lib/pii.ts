// Detect personal identifiers as the person types, so they never leave the browser.
//
// A port of the API's check (src/askoz/answer/pii.py), which stays as the second
// layer for anything calling the API directly. Keep the two in step: the tests
// in pii.test.ts mirror tests/test_pii.py.

const DIGITS = /(?<![\d$])(\d[\d -]{6,13}\d)(?!\d)/g;
const PASSPORT = /\b[A-Z]{1,2}\d{7}\b/;
const EMAIL = /\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b/;
// Australian mobiles and landlines with an area code; not 13/1300/1800 numbers.
const PHONE = /(?<!\d)(?:\+?61[ -]?\(?|\(?0)[2-478]\)?(?:[ -]?\d){8}(?!\d)/;

const TFN_WEIGHTS: Record<number, number[]> = {
  8: [10, 7, 8, 4, 6, 3, 5, 1],
  9: [1, 4, 3, 7, 5, 8, 6, 9, 10],
};
const MEDICARE_WEIGHTS = [1, 3, 7, 9, 1, 3, 7, 9];

const weightedSum = (digits: string, weights: number[]) =>
  weights.reduce((sum, w, i) => sum + Number(digits[i]) * w, 0);

export function isTfn(digits: string): boolean {
  const weights = TFN_WEIGHTS[digits.length];
  return weights !== undefined && weightedSum(digits, weights) % 11 === 0;
}

export function isMedicareNumber(digits: string): boolean {
  if (![10, 11].includes(digits.length) || !"23456".includes(digits[0])) return false;
  return weightedSum(digits.slice(0, 8), MEDICARE_WEIGHTS) % 10 === Number(digits[8]);
}

/** The kinds of identifier in `text` (e.g. ["tax file number"]), never the values. */
export function findIdentifiers(text: string): string[] {
  const found = new Set<string>();
  for (const match of text.matchAll(DIGITS)) {
    const digits = match[1].replace(/[ -]/g, "");
    if (isTfn(digits)) found.add("tax file number");
    if (isMedicareNumber(digits)) found.add("Medicare number");
  }
  if (PASSPORT.test(text)) found.add("passport number");
  if (EMAIL.test(text)) found.add("email address");
  if (PHONE.test(text)) found.add("phone number");
  return [...found].sort();
}

/** "a tax file number", "a tax file number and an email address". */
export function describeIdentifiers(kinds: string[]): string {
  const withArticle = kinds.map((k) => (/^[aeiou]/i.test(k) ? `an ${k}` : `a ${k}`));
  return withArticle.length <= 1
    ? (withArticle[0] ?? "")
    : `${withArticle.slice(0, -1).join(", ")} and ${withArticle.at(-1)}`;
}
