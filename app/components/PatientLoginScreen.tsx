"use client";

import React from "react";
import { LoginScreen } from "./LoginScreen";

export const PatientLoginScreen: React.FC<any> = (props) => {
  return <LoginScreen {...props} initialSignUp={false} />;
};

export default PatientLoginScreen;
