export type SiteContent = {
  format: "corporate-site.visual.v1";
  brand: { name: string; navy: string; blue: string; cyan: string };
  hero: { title: string; accent: string; description: string };
  about: { title: string; description: string };
  services: { title: string; description: string }[];
  plans: { id: string; name: string; price: string; description: string }[];
  faq: { question: string; answer: string }[];
};
