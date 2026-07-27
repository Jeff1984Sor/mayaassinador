"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Usuario = {
  id: number;
  nome: string;
  email: string;
  tenant_id: number;
};

type AuthState = {
  token: string | null;
  usuario: Usuario | null;
  /** false ate o localStorage ser lido. Sem isso o guard de rota
   *  redirecionaria para /login a cada F5, antes da sessao ser restaurada.
   *  Fica fora do partialize: e estado de runtime, nao se persiste. */
  hidratado: boolean;
  entrar: (token: string, usuario: Usuario) => void;
  sair: () => void;
  marcarHidratado: () => void;
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      usuario: null,
      hidratado: false,
      entrar: (token, usuario) => set({ token, usuario }),
      sair: () => set({ token: null, usuario: null }),
      marcarHidratado: () => set({ hidratado: true }),
    }),
    {
      name: "mayaassinador-auth",
      partialize: (s) => ({ token: s.token, usuario: s.usuario }),
      // roda no cliente apos ler o localStorage, mesmo quando esta vazio
      onRehydrateStorage: () => (state) => state?.marcarHidratado(),
    },
  ),
);

/** Token fora do React — usado pelo interceptor do axios. */
export const getToken = () => useAuth.getState().token;
