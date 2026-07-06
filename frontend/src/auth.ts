import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

const adminEmails = (process.env.ADMIN_EMAILS ?? "")
  .split(",")
  .map((email) => email.trim().toLowerCase())
  .filter(Boolean);

function getRole(email?: string | null) {
  return email && adminEmails.includes(email.toLowerCase()) ? "admin" : "user";
}

function normalizeRole(role: unknown) {
  return role === "admin" ? "admin" : "user";
}

async function syncUserToBackend(params: {
  email?: string | null;
  name?: string | null;
  image?: string | null;
  role: "admin" | "user";
  provider?: string;
  providerAccountId?: string;
}) {
  if (!params.email) return;
  const baseUrl = process.env.INTERNAL_API_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    await fetch(`${baseUrl}/auth/sync-user`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: params.email,
        name: params.name,
        image: params.image,
        role: params.role,
        provider: params.provider ?? "google",
        provider_account_id: params.providerAccountId ?? params.email,
      }),
    });
  } catch (error) {
    console.error("Failed to sync authenticated user", error);
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  secret: process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET,
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user, account }) {
      const role = getRole(token.email ?? user?.email);
      token.role = role;
      if (account && (token.email || user?.email)) {
        await syncUserToBackend({
          email: token.email ?? user?.email,
          name: token.name ?? user?.name,
          image: token.picture ?? user?.image,
          role,
          provider: account.provider,
          providerAccountId: account.providerAccountId,
        });
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        session.user.role = normalizeRole(token.role);
      }
      return session;
    },
  },
});