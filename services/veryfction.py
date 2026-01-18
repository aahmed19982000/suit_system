import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tasks.models import Task


def url_form_sitemap_html(sitemap_url, keyword):
    task_review = ['تقييم', 'تحديث/تقييم']

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        read_sitemap = requests.get(sitemap_url, headers=headers, timeout=10)
        print("Status:", read_sitemap.status_code)
        if read_sitemap.status_code != 200:
            print("❌ الصفحة غير موجودة أو هناك مشكلة في الوصول.")
            return []

        soup = BeautifulSoup(read_sitemap.text, "html.parser")

        # =========================
        # معالجة keyword لو كان رابط
        # =========================
        if keyword.startswith("http"):
            parsed = urlparse(keyword)
            keyword = parsed.netloc or parsed.path
            keyword = keyword.replace("www.", "")

            for ext in [".com", ".net", ".org", ".io", ".co", ".ae", ".sa", "تقييم", "شركة", "افضل شركات",'/ar']:
                keyword = keyword.replace(ext, "")

        keyword_words = keyword.lower().split()
        min_match = 2 if len(keyword_words) > 2 else 1

        
        task = Task.objects.filter(article_title=keyword).first()
        if task and task.article_type_W_R_A_B in task_review:
            min_match = 1 if len(keyword_words) > 2 else 1

        reslist = []
        seen_links = set()

        for link in soup.find_all("a"):
            anchor_text = link.get_text(strip=True) or ""
            href = link.get("href")
            if not href:
                continue

            full_href = urljoin(sitemap_url, href)

            if full_href in seen_links:
                continue
            seen_links.add(full_href)

            anchor_words = anchor_text.lower().split()
            match_count = sum(1 for word in keyword_words if word in anchor_words)

            if match_count >= min_match:
                reslist.append((full_href, anchor_text, match_count))

        reslist.sort(key=lambda x: x[2], reverse=True)
        return reslist

    except requests.RequestException as e:
        print("❌ حدث خطأ أثناء محاولة الوصول إلى الصفحة.", str(e))
        return []


# مثال استخدام
sitemap_url = "https://daman.reviews/sitemap"
keyword = "اعادة كتابة تقييم شركة fxcc  بشكل ايجابي"

found_links = url_form_sitemap_html(sitemap_url, keyword)

print("\n🔎 النتائج النهائية (مرتبة حسب عدد الكلمات المتطابقة، بدون تكرار):")
if found_links:
    for href, text, count in found_links:
        print(f"النص: {text}\nالرابط: {href}\nعدد الكلمات المتطابقة: {count}\n---")
else:
    print("❌ لم يتم العثور على أي روابط تحتوي على كلمات من الجملة.")
