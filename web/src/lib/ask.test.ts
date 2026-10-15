import { describe, expect, it } from "vitest";

import { waitText } from "./ask";

describe("waitText", () => {
  it("uses minutes for short waits and hours for long ones", () => {
    expect(waitText(30)).toBe("about 1 minute");
    expect(waitText(42 * 60)).toBe("about 42 minutes");
    expect(waitText(14 * 3600)).toBe("about 14 hours");
    expect(waitText(3600 * 1.6)).toBe("about 2 hours");
  });
});
