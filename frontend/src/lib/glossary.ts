// Plain one-line meanings of land words, Bangla + English. Descriptive only, no legal claims.
export type GlossaryEntry = { term: string; latin: string; bn: string; en: string };

export const glossary: GlossaryEntry[] = [
  { term: "খতিয়ান", latin: "khatian", bn: "জমির রেকর্ড: কোন দাগে কে কতটুকু অংশের মালিক, তা লেখা থাকে।", en: "Record of rights: who owns what share of which plot." },
  { term: "দাগ", latin: "dag", bn: "মৌজা ম্যাপে একটি জমির টুকরার নম্বর।", en: "Plot number on the mouza map." },
  { term: "মৌজা", latin: "mouza", bn: "জরিপের সবচেয়ে ছোট এলাকা; প্রতিটি মৌজার আলাদা ম্যাপ ও খতিয়ান থাকে।", en: "Smallest survey area, each with its own map and records." },
  { term: "নামজারি", latin: "namjari / mutation", bn: "জমি কেনা বা উত্তরাধিকারের পর নতুন মালিকের নামে খতিয়ান খোলা।", en: "Updating the record into the new owner's name." },
  { term: "দলিল", latin: "dalil / deed", bn: "জমি হস্তান্তরের নিবন্ধিত কাগজ, যেমন বিক্রয় দলিল।", en: "Registered transfer document, e.g. a sale deed." },
  { term: "বায়না", latin: "bayna", bn: "জমি কেনার আগে চুক্তি করে দেওয়া অগ্রিম টাকা।", en: "Earnest money paid before the sale." },
  { term: "ওয়ারিশ", latin: "warish / heir", bn: "মৃত মালিকের উত্তরাধিকারী; ওয়ারিশ সনদে তাঁদের নাম থাকে।", en: "Heir of a deceased owner, listed on the heir certificate." },
  { term: "শতাংশ", latin: "shotangsho / decimal", bn: "জমির মাপের একক; ১ একর = ১০০ শতাংশ।", en: "Land unit; 1 acre = 100 decimals." },
  { term: "জরিপ", latin: "CS / SA / RS / BS survey", bn: "যে জরিপে খতিয়ান তৈরি, তার নাম; খতিয়ানে লেখা থাকে (সি.এস., এস.এ., আর.এস., বি.এস.)।", en: "The survey a khatian comes from, printed on it." },
  { term: "আমিন", latin: "amin", bn: "মাঠে জমি মেপে দেখার লোক (সার্ভেয়ার)।", en: "Land surveyor who measures the plot on site." },
];

export const glossaryOf = (term: string) => glossary.find((g) => g.term === term);
