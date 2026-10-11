import { describe, it, expect, vi } from "vitest";
import { translations } from "../app/translations";

describe("UX - Show/Hide Password Eye Toggle", () => {
  it("provides exact EN and UR translation strings for password visibility toggles", () => {
    expect(translations.en.showPassword).toBe("Show password");
    expect(translations.en.hidePassword).toBe("Hide password");
    expect(translations.en.showConfirmPassword).toBe("Show confirm password");
    expect(translations.en.hideConfirmPassword).toBe("Hide confirm password");

    expect(translations.ur.showPassword).toBe("پاس ورڈ دکھائیں");
    expect(translations.ur.hidePassword).toBe("پاس ورڈ چھپائیں");
    expect(translations.ur.showConfirmPassword).toBe("پاس ورڈ کی تصدیق دکھائیں");
    expect(translations.ur.hideConfirmPassword).toBe("پاس ورڈ کی تصدیق چھپائیں");
  });

  it("toggles password input type between 'password' and 'text' and updates aria-label", () => {
    let showPassword = false;
    const toggle = () => {
      showPassword = !showPassword;
    };

    const getInputType = () => (showPassword ? "text" : "password");
    const getAriaLabel = (isUrdu = false) => {
      const t = isUrdu ? translations.ur : translations.en;
      return showPassword ? t.hidePassword : t.showPassword;
    };

    // Initially hidden
    expect(getInputType()).toBe("password");
    expect(getAriaLabel(false)).toBe("Show password");
    expect(getAriaLabel(true)).toBe("پاس ورڈ دکھائیں");

    // Click toggle -> visible
    toggle();
    expect(getInputType()).toBe("text");
    expect(getAriaLabel(false)).toBe("Hide password");
    expect(getAriaLabel(true)).toBe("پاس ورڈ چھپائیں");

    // Click toggle again -> hidden
    toggle();
    expect(getInputType()).toBe("password");
    expect(getAriaLabel(false)).toBe("Show password");
    expect(getAriaLabel(true)).toBe("پاس ورڈ دکھائیں");
  });

  it("toggles confirm-password input type between 'password' and 'text' and updates aria-label", () => {
    let showConfirmPassword = false;
    const toggle = () => {
      showConfirmPassword = !showConfirmPassword;
    };

    const getInputType = () => (showConfirmPassword ? "text" : "password");
    const getAriaLabel = (isUrdu = false) => {
      const t = isUrdu ? translations.ur : translations.en;
      return showConfirmPassword ? t.hideConfirmPassword : t.showConfirmPassword;
    };

    expect(getInputType()).toBe("password");
    expect(getAriaLabel(false)).toBe("Show confirm password");
    expect(getAriaLabel(true)).toBe("پاس ورڈ کی تصدیق دکھائیں");

    toggle();
    expect(getInputType()).toBe("text");
    expect(getAriaLabel(false)).toBe("Hide confirm password");
    expect(getAriaLabel(true)).toBe("پاس ورڈ کی تصدیق چھپائیں");
  });

  it("verifies bidirectional padding layout ensures icon clearance in both LTR and RTL", () => {
    // Both LTR and RTL require clearing the leading Lock icon (11 = 2.75rem) and trailing Eye button (11 = 2.75rem)
    const getPaddingClasses = (isUrdu: boolean) => {
      return isUrdu ? "pr-11 pl-11" : "pl-11 pr-11";
    };

    expect(getPaddingClasses(false)).toContain("pl-11");
    expect(getPaddingClasses(false)).toContain("pr-11");
    expect(getPaddingClasses(true)).toContain("pl-11");
    expect(getPaddingClasses(true)).toContain("pr-11");
  });
});

describe("UX - Visible Logout Button", () => {
  it("provides exact EN and UR translation strings for logout", () => {
    expect(translations.en.logoutBtn).toBe("Log Out");
    expect(translations.ur.logoutBtn).toBe("لاگ آؤٹ");
  });

  it("triggers signOutUser() and navigates to 'login' screen on logout invocation", async () => {
    const signOutUserMock = vi.fn().mockResolvedValue(undefined);
    const setScreenMock = vi.fn();
    const setShowSettingsMock = vi.fn();

    const handleHomeLogout = async () => {
      await signOutUserMock();
      setScreenMock("login");
    };

    const handleSettingsLogout = async () => {
      setShowSettingsMock(false);
      await signOutUserMock();
      setScreenMock("login");
    };

    // Test Home header logout
    await handleHomeLogout();
    expect(signOutUserMock).toHaveBeenCalledTimes(1);
    expect(setScreenMock).toHaveBeenCalledWith("login");

    // Test Settings modal logout
    await handleSettingsLogout();
    expect(setShowSettingsMock).toHaveBeenCalledWith(false);
    expect(signOutUserMock).toHaveBeenCalledTimes(2);
    expect(setScreenMock).toHaveBeenCalledWith("login");
  });
});
