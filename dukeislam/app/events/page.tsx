import type { Metadata } from "next";
import { getEventsPayload } from "@/lib/events";
import { EventsView } from "@/components/events/events-view";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Duke Muslim Life Events & Activities",
  description:
    "Upcoming Duke Islam community events, Jummah prayer schedules, and Muslim Life student gatherings at Duke University.",
  keywords: [
    "Duke Islam events",
    "Duke Muslim Life",
    "Duke MSA",
    "Duke Jummah",
    "Duke University Muslim events",
  ],
};

export default async function EventsPage() {
  const payload = await getEventsPayload();

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-10">
      <PageHeader
        title="What's"
        accent="happening"
        description="Muslim Life events from CML, MSA, and other campus groups."
      />
      <EventsView payload={payload} />
    </div>
  );
}
