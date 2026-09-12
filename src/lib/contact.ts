/** The administrator a teacher reaches to top up a balance.
 *
 * Mirrors the mobile app's lib/core/constants/contact_info.dart — one
 * number, two places, so changing it is two edits rather than a hunt
 * through the UI. `*Digits` are the same numbers without spaces or the
 * plus, which is the form wa.me and tel: links need.
 */
export const CONTACT = {
  whatsapp: "+992 92 841 55 52",
  whatsappDigits: "992928415552",
  phone: "+992 92 841 55 52",
  phoneDigits: "+992928415552",
  telegram: "@tursunboev_mee",
  telegramUrl: "https://t.me/tursunboev_mee",
  email: "tursunboevmahkamjon98@gmail.com",
} as const;
