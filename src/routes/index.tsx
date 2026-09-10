import { createFileRoute } from "@tanstack/react-router";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { Viewport } from "@/components/Viewport";
import { PropertiesPanel } from "@/components/PropertiesPanel";
import { CommandBar } from "@/components/CommandBar";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "GameForge AI — AI-Powered 3D Creation Studio" },
      {
        name: "description",
        content:
          "GameForge AI is a cinematic 3D creation studio: model, material, animate and render game assets from a single prompt.",
      },
      { property: "og:title", content: "GameForge AI — AI-Powered 3D Creation Studio" },
      {
        property: "og:description",
        content:
          "Design game-ready 3D models, materials and animations in one professional AI studio workspace.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Studio,
});

function Studio() {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-background">
      <Header />
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <Viewport />
        <PropertiesPanel />
      </div>
      <CommandBar />
    </main>
  );
}
