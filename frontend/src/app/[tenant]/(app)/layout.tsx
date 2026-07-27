"use client";

import { FileSignature, Loader2, LogOut, Settings } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/store/auth";

const MENU = [
  { href: "documentos", rotulo: "Documentos", Icone: FileSignature },
  { href: "configuracoes", rotulo: "Configuracoes", Icone: Settings },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { tenant } = useParams<{ tenant: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const { token, usuario, hidratado, sair } = useAuth();

  // Guard de rota: so redireciona depois da hidratacao do localStorage.
  useEffect(() => {
    if (hidratado && !token) router.replace(`/${tenant}/login`);
  }, [hidratado, token, tenant, router]);

  if (!hidratado || !token) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-navy/40" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col bg-dark md:flex">
        <div className="flex items-center gap-2.5 px-5 py-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-navy">
            <FileSignature className="h-4 w-4 text-white" />
          </div>
          <span className="font-semibold text-white">MayaAssinador</span>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {MENU.map(({ href, rotulo, Icone }) => {
            const url = `/${tenant}/${href}`;
            const ativo = pathname.startsWith(url);
            return (
              <Link
                key={href}
                href={url}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
                  ativo
                    ? "bg-white/10 font-medium text-white"
                    : "text-white/75 hover:bg-white/5 hover:text-white/95",
                )}
              >
                <Icone className="h-4 w-4" />
                {rotulo}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-white/10 p-3">
          <div className="px-2 pb-2">
            <p className="truncate text-sm font-medium text-white">
              {usuario?.nome}
            </p>
            <p className="truncate text-xs text-white/62">{usuario?.email}</p>
          </div>
          <button
            onClick={() => {
              sair();
              router.replace(`/${tenant}/login`);
            }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm
                       text-white/75 transition hover:bg-white/5 hover:text-white/95"
          >
            <LogOut className="h-4 w-4" />
            Sair
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-x-hidden">{children}</main>
    </div>
  );
}
