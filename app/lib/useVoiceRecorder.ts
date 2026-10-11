import { useState, useRef, useEffect } from "react";
import { api, ApiError, ProfileResponse } from "./api";

export interface UseVoiceRecorderOptions {
  onTranscribed: (text: string) => void;
  isUrdu: boolean;
  profile?: ProfileResponse | null;
}

export function useVoiceRecorder({
  onTranscribed,
  isUrdu,
  profile,
}: UseVoiceRecorderOptions) {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  const cleanupMediaStream = () => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      cleanupMediaStream();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const handleStartRecording = async () => {
    setVoiceError(null);

    if (profile && profile.voice_enabled === false) {
      setVoiceError(
        isUrdu
          ? "آواز کا فیچر سیٹنگز میں بند ہے۔ براہ کرم سیٹنگز میں جا کر اسے آن کریں۔"
          : "Voice input is disabled in your profile. Enable it in Settings (Privacy & Consent) to speak your answers."
      );
      return;
    }

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setVoiceError(
        isUrdu
          ? "آپ کے براؤزر میں مائیکروفون دستیاب نہیں ہے۔ براہ کرم جواب ٹائپ کریں۔"
          : "Microphone recording is not supported in this browser. Please type your answer."
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      let mimeType = "";
      if (typeof MediaRecorder !== "undefined") {
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
          mimeType = "audio/webm;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/webm")) {
          mimeType = "audio/webm";
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
          mimeType = "audio/mp4";
        }
      }

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const chunks = audioChunksRef.current;
        cleanupMediaStream();
        setIsRecording(false);

        if (!chunks || chunks.length === 0) return;

        const audioBlob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });

        if (audioBlob.size > 5 * 1024 * 1024) {
          setVoiceError(
            isUrdu
              ? "آواز کی فائل ۵ ایم بی سے زیادہ ہے۔ براہ کرم مختصر جواب ریکارڈ کریں۔"
              : "Audio recording exceeds the 5MB limit. Please record a shorter answer."
          );
          return;
        }

        if (audioBlob.size < 100) {
          setVoiceError(isUrdu ? "کوئی آواز ریکارڈ نہیں ہوئی۔" : "No audio detected. Please try again.");
          return;
        }

        setIsTranscribing(true);
        setVoiceError(null);

        try {
          const res = await api.transcribeVoice(audioBlob, "recording.webm");
          const text = (res.text || "").trim();
          if (text) {
            onTranscribed(text);
          } else {
            setVoiceError(
              isUrdu
                ? "کوئی الفاظ سمجھ نہیں آئے۔ براہ کرم دوبارہ بولیں یا لکھ کر جواب دیں۔"
                : "No speech recognized. Please try speaking clearly or type your answer."
            );
          }
        } catch (err: any) {
          if (err instanceof ApiError) {
            if (err.status === 403) {
              setVoiceError(
                isUrdu
                  ? "آواز کا فیچر آپ کی پروفائل میں بند ہے۔ سیٹنگز میں فعال کریں۔"
                  : "Voice input is not enabled in your profile settings."
              );
            } else if (err.status === 429) {
              setVoiceError(
                isUrdu
                  ? "آواز کی حد ختم ہو گئی ہے۔ براہ کرم کچھ دیر بعد کوشش کریں یا ٹائپ کریں۔"
                  : "Voice transcription rate limit reached. Please type your answer or wait a minute."
              );
            } else if (err.status === 502 || err.status === 503) {
              setVoiceError(
                isUrdu
                  ? "آواز کی سروس عارضی طور پر غیر فعال ہے۔ براہ کرم جواب ٹائپ کریں۔"
                  : "Voice transcription service temporarily unavailable. Please type your answer."
              );
            } else {
              setVoiceError(err.getFriendlyMessage(isUrdu));
            }
          } else {
            setVoiceError(
              isUrdu
                ? "آواز کی منتقلی میں خرابی پیش آئی۔ براہ کرم جواب ٹائپ کریں۔"
                : "Failed to transcribe voice audio. Please type your answer."
            );
          }
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(1000);
      setIsRecording(true);
      setRecordingSeconds(0);

      let sec = 0;
      recordingTimerRef.current = setInterval(() => {
        sec += 1;
        setRecordingSeconds(sec);
        if (sec >= 60) {
          handleStopRecording();
        }
      }, 1000);
    } catch (err: any) {
      cleanupMediaStream();
      setIsRecording(false);
      setVoiceError(
        isUrdu
          ? "مائیکروفون تک رسائی کی اجازت نہیں ملی۔ براہ کرم براؤزر میں مائیک کی اجازت دیں یا ٹائپ کریں۔"
          : "Microphone access denied. Please allow microphone permissions or type your answer."
      );
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        cleanupMediaStream();
        setIsRecording(false);
      }
    } else {
      cleanupMediaStream();
      setIsRecording(false);
    }
  };

  const handleCancelRecording = () => {
    audioChunksRef.current = [];
    cleanupMediaStream();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    setIsRecording(false);
  };

  return {
    isRecording,
    recordingSeconds,
    isTranscribing,
    voiceError,
    setVoiceError,
    handleStartRecording,
    handleStopRecording,
    handleCancelRecording,
  };
}
