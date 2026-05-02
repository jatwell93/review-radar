export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      <h1 className="text-4xl font-bold text-slate-800 mb-4">Review Radar</h1>
      <p className="text-lg text-slate-500 mb-10 text-center max-w-md">
        Upload your Google reviews and get actionable insights in seconds.
      </p>
      <div id="upload-zone" />
    </div>
  );
}
