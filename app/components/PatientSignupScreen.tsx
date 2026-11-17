"use client";

import React from "react";
import { LoginScreen } from "./LoginScreen";

export const PatientSignupScreen: React.FC<any> = (props) => {
  return <LoginScreen {...props} initialSignUp={true} />;
};

export default PatientSignupScreen;
