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
   *  redirecionaria para /login a cada F5, antes da sessao ser restaurada. */
  hidratado: boolean;
  entrar: (token: string, usuario: Usuario) => void;
  sair: () => void;
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      usuario: null,
      hidratado: false,
      entrar: (token, usuario) => set({ token, usuario }),
      sair: () => set({ token: null, usuario: null }),
    }),
    {
      name: "mayaassinador-auth",
      partialize: (s) => ({ token: s.token, usuario: s.usuario }),
    },
  ),
);

// Marca a hidratacao como concluida. Fica fora do create porque o
// callback do persist roda com o estado ja reconstruido.
useAuth.setState({ hidratado: false });
useAuth.persist.onFinishHydration(() => useAuth.setState({ hidratado: true }));
if (useAuth.persist.hasHydrated()) useAuth.setState({ hidratado: true });

/** Token fora do React — usado pelo interceptor do axios. */
export const getToken = () => useAuth.getState().token;
