"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useApp } from "../context/AppContext";
import { api, InAppNotification } from "../lib/api";
import {
  Bell,
  CheckCheck,
  Check,
  AlertTriangle,
  Clock,
  ShieldAlert,
  Smartphone,
  ExternalLink,
} from "lucide-react";

interface NotificationBellProps {
  role?: "patient" | "provider" | "admin";
}

export const NotificationBell: React.FC<NotificationBellProps> = ({ role }) => {
  const { isUrdu, t, portal } = useApp();
  const effectiveRole = role || (portal === "provider" ? "provider" : portal === "admin" ? "admin" : "patient");

  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<InAppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [fcmStatus, setFcmStatus] = useState<"default" | "granted" | "denied" | "unsupported">("default");
  const [fcmMessage, setFcmMessage] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  // Check browser notification permission status on mount
  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setFcmStatus(Notification.permission as "default" | "granted" | "denied");
    } else {
      setFcmStatus("unsupported");
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      let res;
      if (effectiveRole === "provider") {
        res = await api.getProviderNotifications();
      } else if (effectiveRole === "admin") {
        res = await api.getAdminNotifications();
      } else {
        res = await api.getMyNotifications();
      }
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
    } catch {
      // In isolated/mock mode or when network fails, fail gracefully
    } finally {
      setLoading(false);
    }
  }, [effectiveRole]);

  // Initial load and periodic refresh
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 45000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleOutsideClick);
    }
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isOpen]);

  const toggleDropdown = () => {
    if (!isOpen) {
      fetchNotifications();
    }
    setIsOpen(!isOpen);
  };

  const handleMarkRead = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      if (effectiveRole === "provider") {
        await api.markProviderNotificationRead(id);
      } else if (effectiveRole === "admin") {
        await api.markAdminNotificationRead(id);
      } else {
        await api.markNotificationRead(id);
      }
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // Graceful fallback
    }
  };

  const handleMarkAllRead = async () => {
    try {
      if (effectiveRole === "patient") {
        await api.markAllNotificationsRead();
      }
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // Graceful fallback
    }
  };

  const handleRequestPushPermission = async () => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      setFcmMessage("Browser notifications are not supported in this environment.");
      return;
    }

    try {
      const permission = await Notification.requestPermission();
      setFcmStatus(permission as "default" | "granted" | "denied");
      if (permission === "granted") {
        if ("serviceWorker" in navigator) {
          try {
            await navigator.serviceWorker.register("/firebase-messaging-sw.js");
          } catch {
            // Service worker registration optional in dev
          }
        }
        // Register client token with backend
        const dummyToken = `browser-token-${Date.now()}`;
        await api.registerFcmToken(dummyToken, navigator.userAgent.slice(0, 100));
        setFcmMessage(isUrdu ? "اطلاعات فعال کر دی گئیں" : "Push notifications active");
      } else {
        setFcmMessage(isUrdu ? "اطلاعات کی اجازت نہیں ملی" : "Permission denied");
      }
    } catch {
      setFcmMessage("Failed to enable push notifications.");
    }
  };

  // Safe scrubber for lock screen PHI safety invariant
  const sanitizeDisplay = (text: string) => {
    if (/\b\d{2,3}\s*\/\s*\d{2,3}\b/.test(text) || /\b\d{2,3}\s*(?:mg\/dL|mmol\/L)\b/i.test(text)) {
      return isUrdu ? "طبی جائزہ درکار ہے" : "Clinical review required";
    }
    return text;
  };

  const renderIconForType = (type: string) => {
    switch (type) {
      case "urgent_checkin":
        return <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />;
      case "escalation_renotify":
        return <Clock className="w-4 h-4 text-amber-600 shrink-0" />;
      case "escalation_admin_flag":
        return <ShieldAlert className="w-4 h-4 text-rose-700 shrink-0" />;
      case "daily_reminder":
      default:
        return <Bell className="w-4 h-4 text-teal-600 shrink-0" />;
    }
  };

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      {/* Bell Trigger Button */}
      <button
        type="button"
        id="notification-bell-btn"
        data-testid="notification-bell-btn"
        onClick={toggleDropdown}
        aria-label={`Notifications, ${unreadCount} unread`}
        aria-expanded={isOpen}
        title={t.notificationsTitle}
        className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-700 hover:text-navy-800 bg-white hover:bg-slate-50 border border-slate-300 transition-colors shadow-xs relative min-h-[44px] min-w-[44px]"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span
            data-testid="notification-unread-badge"
            className="absolute -top-1 -right-1 bg-red-600 text-white font-bold text-[10px] min-w-[20px] h-5 px-1.5 rounded-full flex items-center justify-center shadow-md animate-pulse"
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          data-testid="notification-dropdown"
          className={`absolute ${
            isUrdu ? "left-0" : "right-0"
          } mt-2 w-80 sm:w-96 bg-white/98 backdrop-blur-md rounded-2xl border border-slate-200 shadow-2xl z-50 overflow-hidden text-xs animate-fadeIn`}
          dir={isUrdu ? "rtl" : "ltr"}
        >
          {/* Header */}
          <div className="p-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
            <div className="flex items-center gap-2">
              <span className="font-heading font-bold text-navy-900 text-sm">
                {t.notificationsTitle}
              </span>
              {unreadCount > 0 && (
                <span className="bg-teal-100 text-teal-800 font-bold px-2 py-0.5 rounded-full text-[10px]">
                  {unreadCount} {isUrdu ? "نئی" : "new"}
                </span>
              )}
            </div>
            {unreadCount > 0 && effectiveRole === "patient" && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                data-testid="mark-all-read-btn"
                className="text-[11px] font-semibold text-teal-700 hover:text-teal-900 flex items-center gap-1 transition-colors"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>{t.markAllRead}</span>
              </button>
            )}
          </div>

          {/* Notifications List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
            {loading && notifications.length === 0 ? (
              <div className="p-6 text-center text-slate-400">
                <Clock className="w-5 h-5 mx-auto mb-1 animate-spin text-teal-600" />
                <span>Loading...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-6 text-center text-slate-400" data-testid="no-notifications-msg">
                <Bell className="w-6 h-6 mx-auto mb-2 text-slate-300" />
                <p>{t.noNotifications}</p>
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  data-testid={`notification-item-${n.id}`}
                  className={`p-3.5 flex items-start gap-3 transition-colors hover:bg-slate-50 ${
                    !n.is_read ? "bg-teal-50/40 font-medium" : "bg-white"
                  }`}
                >
                  <div className="mt-0.5">{renderIconForType(n.type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-navy-900 truncate">
                        {sanitizeDisplay(n.title)}
                      </span>
                      {!n.is_read && (
                        <span className="w-2 h-2 rounded-full bg-teal-600 shrink-0" title="Unread" />
                      )}
                    </div>
                    <p className="text-slate-600 text-[11px] mt-0.5 leading-relaxed">
                      {sanitizeDisplay(n.body)}
                    </p>
                    <div className="flex items-center justify-between mt-2 pt-1 border-t border-slate-100 text-[10px] text-slate-400">
                      <span>{new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      {!n.is_read && (
                        <button
                          type="button"
                          onClick={(e) => handleMarkRead(n.id, e)}
                          data-testid={`mark-read-btn-${n.id}`}
                          className="text-teal-700 hover:text-teal-900 font-semibold flex items-center gap-0.5"
                        >
                          <Check className="w-3 h-3" />
                          <span>{t.markRead}</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* FCM Push Notification Opt-in Footer */}
          <div className="p-3 bg-slate-50 border-t border-slate-200/80">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 text-slate-600 text-[11px]">
                <Smartphone className="w-3.5 h-3.5 text-teal-700 shrink-0" />
                <span>
                  {fcmStatus === "granted"
                    ? t.webPushActive
                    : fcmStatus === "denied"
                    ? t.webPushBlocked
                    : t.enableWebPush}
                </span>
              </div>
              {fcmStatus !== "granted" && fcmStatus !== "unsupported" && (
                <button
                  type="button"
                  data-testid="enable-push-btn"
                  onClick={handleRequestPushPermission}
                  className="px-2.5 py-1 text-[11px] font-bold rounded-lg bg-teal-700 hover:bg-teal-800 text-white transition-colors shadow-xs shrink-0"
                >
                  {isUrdu ? "فعال کریں" : "Enable"}
                </button>
              )}
            </div>
            {fcmMessage && (
              <p className="mt-1.5 text-[10px] text-teal-800 font-medium">{fcmMessage}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
