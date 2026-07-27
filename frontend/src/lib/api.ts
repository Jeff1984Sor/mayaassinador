"use client";

import axios from "axios";

import { getToken, useAuth } from "@/store/auth";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8030",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    // token expirado ou invalido: derruba a sessao e volta pro login
    if (error?.response?.status === 401 && getToken()) {
      useAuth.getState().sair();
      if (typeof window !== "undefined") {
        const slug = window.location.pathname.split("/")[1] || "escritorio";
        window.location.href = `/${slug}/login`;
      }
    }
    return Promise.reject(error);
  },
);

/** Extrai a mensagem de erro da API no formato do FastAPI. */
export function mensagemErro(e: unknown, padrao = "Algo deu errado"): string {
  if (axios.isAxiosError(e)) {
    const detail = e.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    if (e.code === "ERR_NETWORK") return "Nao foi possivel falar com o servidor";
  }
  return padrao;
}
