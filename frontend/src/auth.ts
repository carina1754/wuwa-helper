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
    jwt({ token }) {
      token.role = getRole(token.email);
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
