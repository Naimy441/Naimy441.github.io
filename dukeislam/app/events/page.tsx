import type { Metadata } from "next";
import { getEventsPayload } from "@/lib/events";
import { EventsView } from "@/components/events/events-view";

export const metadata: Metadata = {
  title: "Events",
  description:
    "Upcoming Muslim Life events at Duke University — from the Center for Muslim Life, MSA, and more.",
};

export default async function EventsPage() {
  const payload = await getEventsPayload();

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-12">
      <div className="mb-6 space-y-2 md:mb-8">
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
          What&apos;s <span className="font-display italic text-primary">happening</span>
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground md:text-base">
          Every Muslim Life event on campus, pulled live from DukeGroups — CML, MSA,
          Grad &amp; Professional MSA, Black Muslim Coalition, SJP, and One for All.
        </p>
      </div>
      <EventsView payload={payload} />
    </div>
  );
}
