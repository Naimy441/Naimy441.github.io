import type { Metadata } from "next";
import { getEventsPayload } from "@/lib/events";
import { EventsView } from "@/components/events/events-view";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = {
  title: "Events",
  description: "Upcoming Muslim Life events at Duke University.",
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
