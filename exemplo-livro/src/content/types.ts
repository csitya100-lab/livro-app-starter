// Único lugar onde os tipos do conteúdo são declarados.
// content/book.json precisa obedecer a este formato (ver fabrica/validate.py).

/** Faixa de interpretação de um exame: vale até `max` (null = sem teto). */
export type Band = {
  max: number | null;
  label: string;
  tone: "alert" | "warn" | "ok" | "info";
};

/** Campo numérico de uma calculadora, com as faixas de interpretação do próprio livro. */
export type Field = {
  id: string;
  label: string;
  unit: string | null;
  min: number;
  max: number;
  step: number;
  initial: number;
  bands: Band[];
};

/** Grupo POSEIDON, na ordem 1 a 4 (jovem/normal, ≥35/normal, jovem/baixa, ≥35/baixa). */
export type PoseidonGroup = {
  label: string;
  detail: string;
  clbr: string;
  clbr3: string;
};

export type Block =
  | { type: "p"; text: string }
  | { type: "h2"; text: string }
  | { type: "h3"; text: string }
  | { type: "image"; key: string; caption: string | null }
  | { type: "table"; rows: string[][] }
  | { type: "pullquote"; text: string; label: string | null }
  | { type: "video"; key: string; caption: string | null; poster: string | null }
  | {
      type: "quiz";
      question: string;
      options: string[];
      answer: number;
      explanation: string | null;
    }
  | {
      type: "flashcard";
      title: string | null;
      cards: { front: string; back: string }[];
    }
  | {
      type: "calc";
      kind: "bands";
      title: string;
      note: string | null;
      fields: Field[];
    }
  | {
      type: "calc";
      kind: "poseidon";
      title: string;
      note: string | null;
      ageLabel: string;
      ageThreshold: number;
      ageInitial: number;
      fields: Field[];
      groups: PoseidonGroup[];
    }
  | {
      type: "chart";
      kind: "decline";
      title: string;
      note: string | null;
      points: { stage: string; value: number; text: string }[];
    };

/** Blocos que a leitura em voz alta percorre (os demais são visuais ou interativos). */
export type TextBlock = Extract<Block, { text: string }>;

export function isTextBlock(block: Block): block is TextBlock {
  return block.type === "p" || block.type === "h2" || block.type === "h3";
}

export type Chapter = {
  id: string;
  number: number | null;
  title: string;
  subtitle: string | null;
  part: string;
  blocks: Block[];
  audioUrl?: string | null;
};
