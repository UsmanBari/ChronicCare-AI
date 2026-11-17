// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { generateConsultationSlots, getNextThreeWorkingDays, formatHourSlot } from "../app/lib/slots";

describe("Consultation Slot Generator (Fixed Clock)", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("formats hours 9:00 to 16:00 properly with AM/PM", () => {
    expect(formatHourSlot(9)).toBe("9:00 AM");
    expect(formatHourSlot(10)).toBe("10:00 AM");
    expect(formatHourSlot(11)).toBe("11:00 AM");
    expect(formatHourSlot(12)).toBe("12:00 PM");
    expect(formatHourSlot(13)).toBe("1:00 PM");
    expect(formatHourSlot(14)).toBe("2:00 PM");
    expect(formatHourSlot(15)).toBe("3:00 PM");
    expect(formatHourSlot(16)).toBe("4:00 PM");
  });

  it("when today is Sunday 15 Nov 2026: tomorrow is Monday, so day+1 is Tomorrow", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-15T10:00:00Z")); // Sunday

    const slots = generateConsultationSlots();
    expect(slots.length).toBe(24); // 3 days * 8 slots

    // Monday (16 Nov) is tomorrow
    expect(slots[0]).toBe("Tomorrow • 9:00 AM");
    expect(slots[1]).toBe("Tomorrow • 10:00 AM");
    expect(slots[7]).toBe("Tomorrow • 4:00 PM");

    // Tuesday (17 Nov)
    expect(slots[8]).toBe("Tuesday, 17 Nov • 9:00 AM");
    expect(slots[15]).toBe("Tuesday, 17 Nov • 4:00 PM");

    // Wednesday (18 Nov)
    expect(slots[16]).toBe("Wednesday, 18 Nov • 9:00 AM");
    expect(slots[23]).toBe("Wednesday, 18 Nov • 4:00 PM");
  });

  it("when today is Friday 13 Nov 2026: skips weekend, Monday is not Tomorrow", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-13T14:30:00Z")); // Friday

    const slots = generateConsultationSlots();
    expect(slots.length).toBe(24);

    // Sat/Sun skipped. First working day is Monday 16 Nov
    expect(slots.some((s) => s.startsWith("Tomorrow"))).toBe(false);
    expect(slots[0]).toBe("Monday, 16 Nov • 9:00 AM");
    expect(slots[8]).toBe("Tuesday, 17 Nov • 9:00 AM");
    expect(slots[16]).toBe("Wednesday, 18 Nov • 9:00 AM");
  });

  it("when today is Thursday 12 Nov 2026: Friday is Tomorrow, next working days skip weekend to Mon and Tue", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-12T09:00:00Z")); // Thursday

    const workingDays = getNextThreeWorkingDays();
    expect(workingDays.length).toBe(3);
    expect(workingDays[0].isTomorrow).toBe(true);
    expect(workingDays[0].date.getDay()).toBe(5); // Friday

    expect(workingDays[1].isTomorrow).toBe(false);
    expect(workingDays[1].date.getDay()).toBe(1); // Monday

    expect(workingDays[2].isTomorrow).toBe(false);
    expect(workingDays[2].date.getDay()).toBe(2); // Tuesday

    const slots = generateConsultationSlots();
    expect(slots[0]).toBe("Tomorrow • 9:00 AM");
    expect(slots[8]).toBe("Monday, 16 Nov • 9:00 AM");
    expect(slots[16]).toBe("Tuesday, 17 Nov • 9:00 AM");
  });
});
