// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { NotificationBell } from "../app/components/NotificationBell";
import { EmergencyScreen } from "../app/components/EmergencyScreen";
import { translations } from "../app/translations";
import { api, InAppNotification } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("In-App Notification Centre & Emergency Screen Alert (PR I4-H)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.portal = "patient";
    mockAppContext.setScreen = vi.fn();
    mockAppContext.returnToHomeAndClearRun = vi.fn();
    mockAppContext.escalationRecorded = false;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("NotificationBell Component", () => {
    it("renders bell trigger button and unread badge count", async () => {
      const mockNotifications: InAppNotification[] = [
        {
          id: "notif-1",
          user_id: "p1",
          role: "patient",
          type: "daily_reminder",
          title: "Daily Check-in Reminder",
          body: "Please log your evening health check-in today.",
          is_read: false,
          created_at: new Date().toISOString(),
        },
      ];

      vi.spyOn(api, "getMyNotifications").mockResolvedValue({
        notifications: mockNotifications,
        unread_count: 1,
      });

      render(<NotificationBell role="patient" />);

      await waitFor(() => {
        const badge = screen.getByTestId("notification-unread-badge");
        expect(badge).toBeTruthy();
        expect(badge.textContent).toBe("1");
      });
    });

    it("opens dropdown on bell click and displays notification list", async () => {
      const mockNotifications: InAppNotification[] = [
        {
          id: "notif-1",
          user_id: "p1",
          role: "patient",
          type: "daily_reminder",
          title: "Daily Check-in Reminder",
          body: "Please log your evening health check-in today.",
          is_read: false,
          created_at: new Date().toISOString(),
        },
      ];

      vi.spyOn(api, "getMyNotifications").mockResolvedValue({
        notifications: mockNotifications,
        unread_count: 1,
      });

      render(<NotificationBell role="patient" />);

      const bellBtn = screen.getByTestId("notification-bell-btn");
      fireEvent.click(bellBtn);

      await waitFor(() => {
        expect(screen.getByTestId("notification-dropdown")).toBeTruthy();
        expect(screen.getByText("Daily Check-in Reminder")).toBeTruthy();
        expect(screen.getByText("Please log your evening health check-in today.")).toBeTruthy();
      });
    });

    it("marks single notification as read when clicking mark-read", async () => {
      const mockNotifications: InAppNotification[] = [
        {
          id: "notif-1",
          user_id: "p1",
          role: "patient",
          type: "daily_reminder",
          title: "Daily Check-in Reminder",
          body: "Please log your evening health check-in today.",
          is_read: false,
          created_at: new Date().toISOString(),
        },
      ];

      vi.spyOn(api, "getMyNotifications").mockResolvedValue({
        notifications: mockNotifications,
        unread_count: 1,
      });

      const markSpy = vi.spyOn(api, "markNotificationRead").mockResolvedValue({
        ...mockNotifications[0],
        is_read: true,
      });

      render(<NotificationBell role="patient" />);

      fireEvent.click(screen.getByTestId("notification-bell-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("mark-read-btn-notif-1")).toBeTruthy();
      });

      fireEvent.click(screen.getByTestId("mark-read-btn-notif-1"));

      await waitFor(() => {
        expect(markSpy).toHaveBeenCalledWith("notif-1");
      });
    });

    it("marks all notifications read when clicking mark all read button", async () => {
      const mockNotifications: InAppNotification[] = [
        {
          id: "notif-1",
          user_id: "p1",
          role: "patient",
          type: "daily_reminder",
          title: "Daily Reminder 1",
          body: "Reminder body 1",
          is_read: false,
          created_at: new Date().toISOString(),
        },
        {
          id: "notif-2",
          user_id: "p1",
          role: "patient",
          type: "daily_reminder",
          title: "Daily Reminder 2",
          body: "Reminder body 2",
          is_read: false,
          created_at: new Date().toISOString(),
        },
      ];

      vi.spyOn(api, "getMyNotifications").mockResolvedValue({
        notifications: mockNotifications,
        unread_count: 2,
      });

      const markAllSpy = vi.spyOn(api, "markAllNotificationsRead").mockResolvedValue({
        updated: 2,
      });

      render(<NotificationBell role="patient" />);

      fireEvent.click(screen.getByTestId("notification-bell-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("mark-all-read-btn")).toBeTruthy();
      });

      fireEvent.click(screen.getByTestId("mark-all-read-btn"));

      await waitFor(() => {
        expect(markAllSpy).toHaveBeenCalled();
      });
    });

    it("displays empty state message when no notifications exist", async () => {
      vi.spyOn(api, "getMyNotifications").mockResolvedValue({
        notifications: [],
        unread_count: 0,
      });

      render(<NotificationBell role="patient" />);

      fireEvent.click(screen.getByTestId("notification-bell-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("no-notifications-msg")).toBeTruthy();
        expect(screen.getByText(translations.en.noNotifications)).toBeTruthy();
      });
    });

    it("sanitizes accidental blood pressure or glucose numbers to enforce PHI guard", async () => {
      const mockNotifications: InAppNotification[] = [
        {
          id: "notif-corrupt",
          user_id: "p1",
          role: "patient",
          type: "urgent_checkin",
          title: "Urgent checkin 140/90",
          body: "Patient blood glucose was 250 mg/dL",
          is_read: false,
          created_at: new Date().toISOString(),
        },
      ];

      vi.spyOn(api, "getMyNotifications").mockResolvedValue({
        notifications: mockNotifications,
        unread_count: 1,
      });

      render(<NotificationBell role="patient" />);

      fireEvent.click(screen.getByTestId("notification-bell-btn"));

      await waitFor(() => {
        // Clinical numbers must NOT appear in the rendered DOM
        expect(screen.queryByText(/140\/90/)).toBeNull();
        expect(screen.queryByText(/250 mg\/dL/)).toBeNull();
        expect(screen.getAllByText("Clinical review required").length).toBe(2);
      });
    });

    it("provider clicking a notification item with reference_id sets selectedPatient and opens case directly", async () => {
      mockAppContext.portal = "provider";
      mockAppContext.setProviderScreen = vi.fn();
      mockAppContext.setSelectedPatient = vi.fn();

      const mockProviderNotif: InAppNotification = {
        id: "notif-prov-emg",
        user_id: "prov-1",
        role: "provider",
        type: "urgent_checkin",
        title: "Emergency Alert: Demo Patient Emergency",
        body: "Emergency check-in from Demo Patient Emergency requires immediate clinical review",
        reference_id: "chk-emg-case-001",
        is_read: false,
        created_at: new Date().toISOString(),
      };

      vi.spyOn(api, "getProviderNotifications").mockResolvedValue({
        notifications: [mockProviderNotif],
        unread_count: 1,
      });

      render(<NotificationBell role="provider" />);

      fireEvent.click(screen.getByTestId("notification-bell-btn"));

      await waitFor(() => {
        expect(screen.getByText("Emergency Alert: Demo Patient Emergency")).toBeTruthy();
      });

      // Click the notification item
      fireEvent.click(screen.getByTestId("notification-item-notif-prov-emg"));

      expect(mockAppContext.setSelectedPatient).toHaveBeenCalledWith("chk-emg-case-001");
      expect(mockAppContext.setProviderScreen).toHaveBeenCalledWith("reconciliation_alert");
    });

    it("provider clicking 'Open case' button links directly to case with stripped renotify suffix", async () => {
      mockAppContext.portal = "provider";
      mockAppContext.setProviderScreen = vi.fn();
      mockAppContext.setSelectedPatient = vi.fn();

      const mockEscalationNotif: InAppNotification = {
        id: "notif-esc-001",
        user_id: "prov-1",
        role: "provider",
        type: "escalation_renotify",
        title: "Urgent Case Follow-up: Tariq Mahmood",
        body: "An urgent case for Tariq Mahmood has remained unacknowledged for over 5 minutes. Review required.",
        reference_id: "chk-tariq-urgent_renotify",
        is_read: false,
        created_at: new Date().toISOString(),
      };

      vi.spyOn(api, "getProviderNotifications").mockResolvedValue({
        notifications: [mockEscalationNotif],
        unread_count: 1,
      });

      render(<NotificationBell role="provider" />);

      fireEvent.click(screen.getByTestId("notification-bell-btn"));

      await waitFor(() => {
        expect(screen.getByText("Urgent Case Follow-up: Tariq Mahmood")).toBeTruthy();
        expect(screen.getByText(/over 5 minutes/)).toBeTruthy();
      });

      // Click the Open case button
      const openBtn = screen.getByTestId("open-case-btn-notif-esc-001");
      fireEvent.click(openBtn);

      expect(mockAppContext.setSelectedPatient).toHaveBeenCalledWith("chk-tariq-urgent");
      expect(mockAppContext.setProviderScreen).toHaveBeenCalledWith("reconciliation_alert");
    });
  });

  describe("EmergencyScreen Alert Sentence (N4 Requirement)", () => {
    it("shows emergencyReviewListText when escalationRecorded is false", () => {
      mockAppContext.escalationRecorded = false;
      render(<EmergencyScreen />);

      expect(screen.getByText(translations.en.emergencyReviewListText)).toBeTruthy();
      expect(screen.queryByText(translations.en.emergencyAlertedText)).toBeNull();
    });

    it("shows emergencyAlertedText only when escalationRecorded is true", () => {
      mockAppContext.escalationRecorded = true;
      render(<EmergencyScreen />);

      expect(screen.getByText(translations.en.emergencyAlertedText)).toBeTruthy();
      expect(screen.queryByText(translations.en.emergencyReviewListText)).toBeNull();
    });
  });
});
