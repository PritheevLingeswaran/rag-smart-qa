import { auth } from "@/auth";
import { redirect } from "next/navigation";
import AppSidebar from "@/components/app/AppSidebar";
import AppTopBar from "@/components/app/AppTopBar";
import styles from "./layout.module.css";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session) redirect("/signin");

  return (
    <div className={styles.layout}>
      <AppSidebar user={session.user} />
      <div className={styles.right}>
        <AppTopBar user={session.user} />
        <main className={styles.main}>{children}</main>
      </div>
    </div>
  );
}
