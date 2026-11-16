/**
 * Slot generator for provider clinical appointments.
 * Generates consultation slots for the next 3 working days (skipping Sat/Sun),
 * 9:00 to 17:00 in 1-hour increments (9:00 to 16:00).
 */

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatHourSlot(hour: number): string {
  const h12 = hour === 12 ? 12 : hour % 12;
  const ampm = hour >= 12 ? "PM" : "AM";
  return `${h12}:00 ${ampm}`;
}

export function formatDayLabel(targetDate: Date, isTomorrowWorkingDay: boolean): string {
  if (isTomorrowWorkingDay) {
    return "Tomorrow";
  }
  const weekday = WEEKDAYS[targetDate.getDay()];
  const day = targetDate.getDate();
  const month = MONTHS[targetDate.getMonth()];
  return `${weekday}, ${day} ${month}`;
}

export function getNextThreeWorkingDays(baseDate: Date = new Date()): { date: Date; isTomorrow: boolean }[] {
  const workingDays: { date: Date; isTomorrow: boolean }[] = [];
  let dayOffset = 1;

  while (workingDays.length < 3) {
    const candidate = new Date(baseDate.getFullYear(), baseDate.getMonth(), baseDate.getDate() + dayOffset);
    const dayOfWeek = candidate.getDay();
    // 0 = Sunday, 6 = Saturday
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      workingDays.push({
        date: candidate,
        isTomorrow: dayOffset === 1,
      });
    }
    dayOffset++;
  }

  return workingDays;
}

export function generateConsultationSlots(baseDate: Date = new Date()): string[] {
  const workingDays = getNextThreeWorkingDays(baseDate);
  const slots: string[] = [];
  const hours = [9, 10, 11, 12, 13, 14, 15, 16]; // 9:00 to 17:00 (last slot starts at 16:00)

  for (const { date, isTomorrow } of workingDays) {
    const dayLabel = formatDayLabel(date, isTomorrow);
    for (const hour of hours) {
      const timeStr = formatHourSlot(hour);
      slots.push(`${dayLabel} • ${timeStr}`);
    }
  }

  return slots;
}
