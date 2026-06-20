# Dewey + Congress Library Hibrit Kütüphane Kuralları

## Genel Yapı

Bu repo, Dewey Decimal Classification + Library of Congress Classification sistemlerinin hibrit bir versiyonunu kullanır.

## KAT - SALON - RAF Mantığı

- **KAT**: Agent bazlı bölümler (claude-code, cursor, gemini-cli vb.)
- **SALON**: Dewey + Congress tarzı konu bazlı ana kategoriler (000, 200, 600, 900...)
- **RAF**: Bireysel skill veya alt konu

## Kategori Kodları (Ana Salonlar)

- 000: General AI Systems
- 200: Visa & Oturum
- 600: Business & Trade
- 900: History, Geography & Travel

## Güncelleme Kuralları

- Her yeni skill ilgili SALON’un INDEX.md dosyasına eklenmelidir.
- Version numarası her güncellemede artırılmalıdır.
- Self-Learning ile öğrenilen yeni bilgiler resmi kaynaklarla teyit edildikten sonra eklenmelidir.