import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "تجربة عربية" };

export default function ArabicPage() {
  return (
    <main
      id="main-content"
      className="content-page shell arabic-page"
      dir="rtl"
      lang="ar"
    >
      <div className="page-intro">
        <div>
          <p className="kicker">تجربة باللغة العربية</p>
          <h1>مراجعة المستندات مع الحفاظ على الدليل.</h1>
          <p>
            تستخرج المنصة البيانات المنظمة، وتتحقق من الأرقام والتواريخ، وتربط
            كل قيمة بالصفحة المصدر.
          </p>
        </div>
      </div>
      <div className="arabic-feature-grid">
        <article>
          <span>١</span>
          <h2>استخراج منظم</h2>
          <p>حقول واضحة للفواتير وعروض الأسعار وأوامر الشراء والعقود.</p>
        </article>
        <article>
          <span>٢</span>
          <h2>تحقق حتمي</h2>
          <p>قواعد صريحة للمجاميع والضريبة والتواريخ والحقول المطلوبة.</p>
        </article>
        <article>
          <span>٣</span>
          <h2>مراجعة بشرية</h2>
          <p>تصحيح القيم وحفظ سجل التعديلات قبل الاعتماد.</p>
        </article>
      </div>
      <Link className="button button-primary" href="/demo">
        فتح المستند التجريبي
      </Link>
    </main>
  );
}
