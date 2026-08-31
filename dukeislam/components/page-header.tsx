export function PageHeader({
  title,
  accent,
  description,
}: {
  title: string;
  accent?: string;
  description: string;
}) {
  return (
    <div className="mb-6 space-y-2 md:mb-8">
      <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
        {title}
        {accent ? (
          <>
            {" "}
            <span className="font-display italic text-primary">{accent}</span>
          </>
        ) : null}
      </h1>
      <p className="max-w-xl text-sm leading-relaxed text-muted-foreground md:text-base">
        {description}
      </p>
    </div>
  );
}
