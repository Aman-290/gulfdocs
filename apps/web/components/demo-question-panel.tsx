"use client";

import { useState } from "react";
import { FileSearch, MessageSquareText } from "lucide-react";
import type { DemoQuestion } from "@/lib/public-demo";

export function DemoQuestionPanel({
  questions,
}: {
  questions: readonly DemoQuestion[];
}) {
  const [selectedId, setSelectedId] = useState(questions[0]?.id ?? "");
  const selected = questions.find((question) => question.id === selectedId);

  return (
    <section className="question-panel" aria-labelledby="question-heading">
      <div className="panel-heading">
        <MessageSquareText size={19} aria-hidden="true" />
        <div>
          <span>Ask GulfDocs</span>
          <small>Precomputed to protect public-demo quota</small>
        </div>
      </div>
      <h2 id="question-heading" className="sr-only">
        Ask a supported demo question
      </h2>
      <div
        className="question-options"
        role="group"
        aria-label="Supported questions"
      >
        {questions.map((question) => (
          <button
            className={selectedId === question.id ? "active" : ""}
            key={question.id}
            onClick={() => setSelectedId(question.id)}
            type="button"
          >
            {question.question}
          </button>
        ))}
      </div>
      {selected && (
        <div className="answer-card" aria-live="polite">
          <span>Grounded answer</span>
          <p>{selected.answer}</p>
          <a href={`#page-${selected.page}`}>
            <FileSearch size={15} aria-hidden="true" /> Page {selected.page}
          </a>
          <blockquote>{selected.excerpt}</blockquote>
        </div>
      )}
    </section>
  );
}
