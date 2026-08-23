import { revalidatePath, revalidateTag } from "next/cache";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Called by the GitHub Actions scraper right after it pushes fresh menu data,
 * so the site updates immediately instead of waiting out the timed
 * revalidation window. Guarded by the REVALIDATE_SECRET env var (set the same
 * value in Vercel and as a GitHub Actions secret).
 */
export async function GET(req: NextRequest) {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret || req.nextUrl.searchParams.get("secret") !== secret) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }

  revalidateTag("menus", "max");
  revalidatePath("/");
  revalidatePath("/food");

  return NextResponse.json({ ok: true, revalidated: ["menus", "/", "/food"] });
}
