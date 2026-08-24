package com.vardath.janus;

import android.content.Context;

import java.util.Collections;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * High-frequency native-shell translations.
 *
 * JANUS conversation/speech can use the full Android locale catalogue. Static UI
 * translation is intentionally curated: if a phrase or language is not covered,
 * the original English text remains visible rather than applying unsafe runtime
 * machine translation to account/security controls.
 */
final class JanusUiTranslations {
    private static final Map<String, Map<String, String>> LANGUAGES = build();
    private JanusUiTranslations() {}

    static String translate(Context context, String english) {
        if (english == null || english.isEmpty()) return english;
        Locale locale = JanusLanguageSettings.responseLocale(context);
        String language = locale.getLanguage();
        if (language == null || language.isBlank() || "en".equals(language)) return english;
        String key = language;
        if ("zh".equals(language)) {
            String tag = locale.toLanguageTag().toLowerCase(Locale.ROOT);
            key = (tag.contains("hant") || tag.endsWith("-tw") || tag.endsWith("-hk") || tag.endsWith("-mo")) ? "zh-Hant" : "zh-Hans";
        }
        Map<String, String> map = LANGUAGES.get(key);
        if (map == null) return english;
        String direct = map.get(english);
        if (direct != null) return direct;

        // Preserve changing detail after common status/error prefixes.
        for (String prefix : new String[]{"Sign-in failed · ", "Google sign-in failed · ", "JANUS reply failed · ", "Error · "}) {
            if (english.startsWith(prefix)) {
                String translatedPrefix = map.get(prefix.trim());
                if (translatedPrefix != null) return translatedPrefix + " · " + english.substring(prefix.length());
            }
        }
        return english;
    }

    static boolean isRightToLeft(Context context) {
        String language = JanusLanguageSettings.responseLocale(context).getLanguage();
        return "ar".equals(language) || "fa".equals(language) || "he".equals(language) || "ur".equals(language);
    }

    private static Map<String, Map<String, String>> build() {
        Map<String, Map<String, String>> all = new HashMap<>();
        all.put("es", es()); all.put("fr", fr()); all.put("de", de()); all.put("pt", pt());
        all.put("it", it()); all.put("nl", nl()); all.put("pl", pl()); all.put("tr", tr());
        all.put("ru", ru()); all.put("uk", uk()); all.put("ar", ar()); all.put("fa", fa());
        all.put("he", he()); all.put("ur", ur()); all.put("hi", hi()); all.put("bn", bn());
        all.put("id", id()); all.put("vi", vi()); all.put("th", th()); all.put("ja", ja());
        all.put("ko", ko()); all.put("zh-Hans", zhHans()); all.put("zh-Hant", zhHant());
        return Collections.unmodifiableMap(all);
    }

    private static Map<String, String> m(String... pairs) {
        Map<String, String> map = new HashMap<>();
        for (int i = 0; i + 1 < pairs.length; i += 2) map.put(pairs[i], pairs[i + 1]);
        return Collections.unmodifiableMap(map);
    }

    private static String[] commonKeys() { return new String[]{
            "Sign in","Create account","Continue with Google","Forgot password","Reset password","Verify / resend email",
            "Username or email","Password","Username","Email","Connecting to JANUS…","Sign-in failed",
            "Chat","Messages","Observe","Options","Send","Message JANUS","All","Thoughts","Interactions","Refresh snapshot",
            "Cores","Memory","Activity","System status","Compatibility","Research workspace","Artifacts","Background research",
            "Maintenance review","Settings","Account","Language","Appearance","Sign out this device","Sign out all devices",
            "Delete account","Cancel","Close","← Options","Runtime Cores","Loading local and global JANUS runtimes…",
            "THIS DEVICE · LOCAL JANUS","ONLINE · GLOBAL JANUS","No observable core activity in this snapshot.","Technical details"
    }; }

    private static Map<String,String> map(String... values) {
        String[] keys = commonKeys();
        if (values.length != keys.length) throw new IllegalStateException("Translation catalogue length mismatch");
        Map<String,String> out = new HashMap<>();
        for (int i=0;i<keys.length;i++) out.put(keys[i], values[i]);
        out.put("Google sign-in failed", values[11]);
        out.put("JANUS reply failed", values[11]);
        out.put("Error", values[11]);
        return Collections.unmodifiableMap(out);
    }

    private static Map<String,String> es(){return map(
            "Iniciar sesión","Crear cuenta","Continuar con Google","Olvidé mi contraseña","Restablecer contraseña","Verificar / reenviar correo",
            "Usuario o correo","Contraseña","Usuario","Correo electrónico","Conectando con JANUS…","Error al iniciar sesión",
            "Chat","Mensajes","Observar","Opciones","Enviar","Mensaje para JANUS","Todo","Pensamientos","Interacciones","Actualizar vista",
            "Núcleos","Memoria","Actividad","Estado del sistema","Compatibilidad","Espacio de investigación","Artefactos","Investigación en segundo plano",
            "Revisión de mantenimiento","Configuración","Cuenta","Idioma","Apariencia","Cerrar sesión en este dispositivo","Cerrar sesión en todos los dispositivos",
            "Eliminar cuenta","Cancelar","Cerrar","← Opciones","Núcleos en ejecución","Cargando JANUS local y global…",
            "ESTE DISPOSITIVO · JANUS LOCAL","EN LÍNEA · JANUS GLOBAL","No hay actividad observable en esta vista.","Detalles técnicos");}
    private static Map<String,String> fr(){return map(
            "Se connecter","Créer un compte","Continuer avec Google","Mot de passe oublié","Réinitialiser le mot de passe","Vérifier / renvoyer l’e-mail",
            "Nom d’utilisateur ou e-mail","Mot de passe","Nom d’utilisateur","E-mail","Connexion à JANUS…","Échec de la connexion",
            "Discussion","Messages","Observer","Options","Envoyer","Message à JANUS","Tout","Pensées","Interactions","Actualiser l’instantané",
            "Cœurs","Mémoire","Activité","État du système","Compatibilité","Espace de recherche","Artefacts","Recherche en arrière-plan",
            "Révision de maintenance","Paramètres","Compte","Langue","Apparence","Se déconnecter de cet appareil","Se déconnecter de tous les appareils",
            "Supprimer le compte","Annuler","Fermer","← Options","Cœurs actifs","Chargement de JANUS local et global…",
            "CET APPAREIL · JANUS LOCAL","EN LIGNE · JANUS GLOBAL","Aucune activité observable dans cet instantané.","Détails techniques");}
    private static Map<String,String> de(){return map(
            "Anmelden","Konto erstellen","Mit Google fortfahren","Passwort vergessen","Passwort zurücksetzen","E-Mail bestätigen / erneut senden",
            "Benutzername oder E-Mail","Passwort","Benutzername","E-Mail","Verbindung mit JANUS…","Anmeldung fehlgeschlagen",
            "Chat","Nachrichten","Beobachten","Optionen","Senden","Nachricht an JANUS","Alle","Gedanken","Interaktionen","Momentaufnahme aktualisieren",
            "Kerne","Gedächtnis","Aktivität","Systemstatus","Kompatibilität","Forschungsbereich","Artefakte","Hintergrundforschung",
            "Wartungsprüfung","Einstellungen","Konto","Sprache","Darstellung","Auf diesem Gerät abmelden","Auf allen Geräten abmelden",
            "Konto löschen","Abbrechen","Schließen","← Optionen","Laufzeit-Kerne","Lokales und globales JANUS wird geladen…",
            "DIESES GERÄT · LOKALES JANUS","ONLINE · GLOBALES JANUS","Keine beobachtbare Kernaktivität in dieser Momentaufnahme.","Technische Details");}
    private static Map<String,String> pt(){return map(
            "Entrar","Criar conta","Continuar com Google","Esqueci a senha","Redefinir senha","Verificar / reenviar e-mail",
            "Usuário ou e-mail","Senha","Usuário","E-mail","Conectando ao JANUS…","Falha ao entrar",
            "Chat","Mensagens","Observar","Opções","Enviar","Mensagem para JANUS","Tudo","Pensamentos","Interações","Atualizar instantâneo",
            "Núcleos","Memória","Atividade","Status do sistema","Compatibilidade","Área de pesquisa","Artefatos","Pesquisa em segundo plano",
            "Revisão de manutenção","Configurações","Conta","Idioma","Aparência","Sair deste dispositivo","Sair de todos os dispositivos",
            "Excluir conta","Cancelar","Fechar","← Opções","Núcleos em execução","Carregando JANUS local e global…",
            "ESTE DISPOSITIVO · JANUS LOCAL","ONLINE · JANUS GLOBAL","Nenhuma atividade observável neste instantâneo.","Detalhes técnicos");}
    private static Map<String,String> it(){return map(
            "Accedi","Crea account","Continua con Google","Password dimenticata","Reimposta password","Verifica / reinvia e-mail",
            "Nome utente o e-mail","Password","Nome utente","E-mail","Connessione a JANUS…","Accesso non riuscito",
            "Chat","Messaggi","Osserva","Opzioni","Invia","Messaggio a JANUS","Tutto","Pensieri","Interazioni","Aggiorna istantanea",
            "Core","Memoria","Attività","Stato del sistema","Compatibilità","Spazio di ricerca","Artefatti","Ricerca in background",
            "Revisione manutenzione","Impostazioni","Account","Lingua","Aspetto","Esci da questo dispositivo","Esci da tutti i dispositivi",
            "Elimina account","Annulla","Chiudi","← Opzioni","Core in esecuzione","Caricamento JANUS locale e globale…",
            "QUESTO DISPOSITIVO · JANUS LOCALE","ONLINE · JANUS GLOBALE","Nessuna attività osservabile in questa istantanea.","Dettagli tecnici");}
    private static Map<String,String> nl(){return map(
            "Inloggen","Account maken","Doorgaan met Google","Wachtwoord vergeten","Wachtwoord herstellen","E-mail verifiëren / opnieuw verzenden",
            "Gebruikersnaam of e-mail","Wachtwoord","Gebruikersnaam","E-mail","Verbinden met JANUS…","Inloggen mislukt",
            "Chat","Berichten","Observeren","Opties","Verzenden","Bericht aan JANUS","Alles","Gedachten","Interacties","Momentopname vernieuwen",
            "Kernen","Geheugen","Activiteit","Systeemstatus","Compatibiliteit","Onderzoeksruimte","Artefacten","Achtergrondonderzoek",
            "Onderhoudscontrole","Instellingen","Account","Taal","Weergave","Afmelden op dit apparaat","Afmelden op alle apparaten",
            "Account verwijderen","Annuleren","Sluiten","← Opties","Actieve kernen","Lokale en globale JANUS laden…",
            "DIT APPARAAT · LOKALE JANUS","ONLINE · GLOBALE JANUS","Geen observeerbare kernactiviteit in deze momentopname.","Technische details");}
    private static Map<String,String> pl(){return map(
            "Zaloguj się","Utwórz konto","Kontynuuj z Google","Nie pamiętam hasła","Zresetuj hasło","Zweryfikuj / wyślij e-mail ponownie",
            "Nazwa użytkownika lub e-mail","Hasło","Nazwa użytkownika","E-mail","Łączenie z JANUS…","Logowanie nie powiodło się",
            "Czat","Wiadomości","Obserwuj","Opcje","Wyślij","Wiadomość do JANUS","Wszystko","Myśli","Interakcje","Odśwież migawkę",
            "Rdzenie","Pamięć","Aktywność","Stan systemu","Zgodność","Obszar badań","Artefakty","Badania w tle",
            "Przegląd konserwacji","Ustawienia","Konto","Język","Wygląd","Wyloguj na tym urządzeniu","Wyloguj na wszystkich urządzeniach",
            "Usuń konto","Anuluj","Zamknij","← Opcje","Rdzenie wykonawcze","Ładowanie lokalnego i globalnego JANUS…",
            "TO URZĄDZENIE · LOKALNY JANUS","ONLINE · GLOBALNY JANUS","Brak obserwowalnej aktywności rdzeni w tej migawce.","Szczegóły techniczne");}
    private static Map<String,String> tr(){return map(
            "Oturum aç","Hesap oluştur","Google ile devam et","Şifremi unuttum","Şifreyi sıfırla","E-postayı doğrula / yeniden gönder",
            "Kullanıcı adı veya e-posta","Şifre","Kullanıcı adı","E-posta","JANUS’a bağlanılıyor…","Oturum açılamadı",
            "Sohbet","Mesajlar","Gözlemle","Seçenekler","Gönder","JANUS’a mesaj","Tümü","Düşünceler","Etkileşimler","Anlık görüntüyü yenile",
            "Çekirdekler","Bellek","Etkinlik","Sistem durumu","Uyumluluk","Araştırma alanı","Eserler","Arka plan araştırması",
            "Bakım incelemesi","Ayarlar","Hesap","Dil","Görünüm","Bu cihazdan çıkış yap","Tüm cihazlardan çıkış yap",
            "Hesabı sil","İptal","Kapat","← Seçenekler","Çalışma çekirdekleri","Yerel ve küresel JANUS yükleniyor…",
            "BU CİHAZ · YEREL JANUS","ÇEVRİMİÇİ · KÜRESEL JANUS","Bu anlık görüntüde gözlemlenebilir çekirdek etkinliği yok.","Teknik ayrıntılar");}
    private static Map<String,String> ru(){return map(
            "Войти","Создать аккаунт","Продолжить с Google","Забыли пароль","Сбросить пароль","Подтвердить / отправить письмо снова",
            "Имя пользователя или эл. почта","Пароль","Имя пользователя","Эл. почта","Подключение к JANUS…","Не удалось войти",
            "Чат","Сообщения","Наблюдение","Параметры","Отправить","Сообщение JANUS","Все","Мысли","Взаимодействия","Обновить снимок",
            "Ядра","Память","Активность","Состояние системы","Совместимость","Рабочая область исследований","Артефакты","Фоновое исследование",
            "Проверка обслуживания","Настройки","Аккаунт","Язык","Оформление","Выйти на этом устройстве","Выйти на всех устройствах",
            "Удалить аккаунт","Отмена","Закрыть","← Параметры","Рабочие ядра","Загрузка локального и глобального JANUS…",
            "ЭТО УСТРОЙСТВО · ЛОКАЛЬНЫЙ JANUS","ОНЛАЙН · ГЛОБАЛЬНЫЙ JANUS","В этом снимке нет наблюдаемой активности ядер.","Технические детали");}
    private static Map<String,String> uk(){return map(
            "Увійти","Створити обліковий запис","Продовжити з Google","Забули пароль","Скинути пароль","Підтвердити / надіслати лист повторно",
            "Ім’я користувача або ел. пошта","Пароль","Ім’я користувача","Ел. пошта","Підключення до JANUS…","Не вдалося увійти",
            "Чат","Повідомлення","Спостереження","Параметри","Надіслати","Повідомлення JANUS","Усе","Думки","Взаємодії","Оновити знімок",
            "Ядра","Пам’ять","Активність","Стан системи","Сумісність","Простір досліджень","Артефакти","Фонове дослідження",
            "Перегляд обслуговування","Налаштування","Обліковий запис","Мова","Вигляд","Вийти на цьому пристрої","Вийти на всіх пристроях",
            "Видалити обліковий запис","Скасувати","Закрити","← Параметри","Робочі ядра","Завантаження локального й глобального JANUS…",
            "ЦЕЙ ПРИСТРІЙ · ЛОКАЛЬНИЙ JANUS","ОНЛАЙН · ГЛОБАЛЬНИЙ JANUS","У цьому знімку немає спостережуваної активності ядер.","Технічні деталі");}
    private static Map<String,String> ar(){return map(
            "تسجيل الدخول","إنشاء حساب","المتابعة باستخدام Google","نسيت كلمة المرور","إعادة تعيين كلمة المرور","تحقق / أعد إرسال البريد",
            "اسم المستخدم أو البريد الإلكتروني","كلمة المرور","اسم المستخدم","البريد الإلكتروني","جارٍ الاتصال بـ JANUS…","فشل تسجيل الدخول",
            "الدردشة","الرسائل","المراقبة","الخيارات","إرسال","رسالة إلى JANUS","الكل","الأفكار","التفاعلات","تحديث اللقطة",
            "الأنوية","الذاكرة","النشاط","حالة النظام","التوافق","مساحة البحث","الملفات الناتجة","بحث في الخلفية",
            "مراجعة الصيانة","الإعدادات","الحساب","اللغة","المظهر","تسجيل الخروج من هذا الجهاز","تسجيل الخروج من جميع الأجهزة",
            "حذف الحساب","إلغاء","إغلاق","الخيارات ←","أنوية التشغيل","جارٍ تحميل JANUS المحلي والعالمي…",
            "هذا الجهاز · JANUS المحلي","متصل · JANUS العالمي","لا يوجد نشاط أنوية قابل للمراقبة في هذه اللقطة.","تفاصيل تقنية");}
    private static Map<String,String> fa(){return map(
            "ورود","ایجاد حساب","ادامه با Google","رمز عبور را فراموش کرده‌ام","بازنشانی رمز عبور","تأیید / ارسال دوباره ایمیل",
            "نام کاربری یا ایمیل","رمز عبور","نام کاربری","ایمیل","در حال اتصال به JANUS…","ورود ناموفق بود",
            "گفتگو","پیام‌ها","مشاهده","گزینه‌ها","ارسال","پیام به JANUS","همه","افکار","تعامل‌ها","تازه‌سازی نما",
            "هسته‌ها","حافظه","فعالیت","وضعیت سیستم","سازگاری","فضای پژوهش","مصنوعات","پژوهش پس‌زمینه",
            "بازبینی نگهداری","تنظیمات","حساب","زبان","ظاهر","خروج از این دستگاه","خروج از همه دستگاه‌ها",
            "حذف حساب","لغو","بستن","گزینه‌ها ←","هسته‌های اجرا","در حال بارگذاری JANUS محلی و جهانی…",
            "این دستگاه · JANUS محلی","آنلاین · JANUS جهانی","در این نما فعالیت هسته‌ای قابل مشاهده‌ای نیست.","جزئیات فنی");}
    private static Map<String,String> he(){return map(
            "התחברות","יצירת חשבון","המשך עם Google","שכחתי סיסמה","איפוס סיסמה","אימות / שליחה חוזרת של דוא״ל",
            "שם משתמש או דוא״ל","סיסמה","שם משתמש","דוא״ל","מתחבר ל-JANUS…","ההתחברות נכשלה",
            "צ׳אט","הודעות","תצפית","אפשרויות","שליחה","הודעה ל-JANUS","הכול","מחשבות","אינטראקציות","רענון תמונת מצב",
            "ליבות","זיכרון","פעילות","מצב מערכת","תאימות","מרחב מחקר","תוצרים","מחקר ברקע",
            "סקירת תחזוקה","הגדרות","חשבון","שפה","מראה","התנתקות מהמכשיר הזה","התנתקות מכל המכשירים",
            "מחיקת חשבון","ביטול","סגירה","אפשרויות ←","ליבות פעילות","טוען JANUS מקומי וגלובלי…",
            "המכשיר הזה · JANUS מקומי","מקוון · JANUS גלובלי","אין פעילות ליבות נצפית בתמונת המצב הזו.","פרטים טכניים");}
    private static Map<String,String> ur(){return map(
            "سائن اِن","اکاؤنٹ بنائیں","Google کے ساتھ جاری رکھیں","پاس ورڈ بھول گئے","پاس ورڈ ری سیٹ کریں","ای میل کی توثیق / دوبارہ ارسال",
            "صارف نام یا ای میل","پاس ورڈ","صارف نام","ای میل","JANUS سے رابطہ ہو رہا ہے…","سائن اِن ناکام",
            "چیٹ","پیغامات","مشاہدہ","اختیارات","بھیجیں","JANUS کو پیغام","سب","خیالات","تعاملات","اسنیپ شاٹ تازہ کریں",
            "کورز","میموری","سرگرمی","سسٹم کی حالت","مطابقت","تحقیقی جگہ","آرٹی فیکٹس","پس منظر تحقیق",
            "دیکھ بھال کا جائزہ","ترتیبات","اکاؤنٹ","زبان","ظاہری شکل","اس ڈیوائس سے سائن آؤٹ","تمام ڈیوائسز سے سائن آؤٹ",
            "اکاؤنٹ حذف کریں","منسوخ","بند کریں","اختیارات ←","رن ٹائم کورز","مقامی اور عالمی JANUS لوڈ ہو رہا ہے…",
            "یہ ڈیوائس · مقامی JANUS","آن لائن · عالمی JANUS","اس اسنیپ شاٹ میں قابل مشاہدہ کور سرگرمی نہیں ہے۔","تکنیکی تفصیلات");}
    private static Map<String,String> hi(){return map(
            "साइन इन करें","खाता बनाएँ","Google के साथ जारी रखें","पासवर्ड भूल गए","पासवर्ड रीसेट करें","ईमेल सत्यापित / फिर भेजें",
            "उपयोगकर्ता नाम या ईमेल","पासवर्ड","उपयोगकर्ता नाम","ईमेल","JANUS से कनेक्ट हो रहा है…","साइन इन विफल",
            "चैट","संदेश","अवलोकन","विकल्प","भेजें","JANUS को संदेश","सभी","विचार","इंटरैक्शन","स्नैपशॉट ताज़ा करें",
            "कोर","मेमोरी","गतिविधि","सिस्टम स्थिति","संगतता","अनुसंधान कार्यक्षेत्र","आर्टिफैक्ट","पृष्ठभूमि अनुसंधान",
            "रखरखाव समीक्षा","सेटिंग्स","खाता","भाषा","दिखावट","इस डिवाइस से साइन आउट","सभी डिवाइस से साइन आउट",
            "खाता हटाएँ","रद्द करें","बंद करें","← विकल्प","रनटाइम कोर","स्थानीय और वैश्विक JANUS लोड हो रहा है…",
            "यह डिवाइस · स्थानीय JANUS","ऑनलाइन · वैश्विक JANUS","इस स्नैपशॉट में कोई अवलोकनीय कोर गतिविधि नहीं है।","तकनीकी विवरण");}
    private static Map<String,String> bn(){return map(
            "সাইন ইন","অ্যাকাউন্ট তৈরি করুন","Google দিয়ে চালিয়ে যান","পাসওয়ার্ড ভুলে গেছেন","পাসওয়ার্ড রিসেট করুন","ইমেইল যাচাই / আবার পাঠান",
            "ব্যবহারকারীর নাম বা ইমেইল","পাসওয়ার্ড","ব্যবহারকারীর নাম","ইমেইল","JANUS-এ সংযোগ হচ্ছে…","সাইন ইন ব্যর্থ",
            "চ্যাট","বার্তা","পর্যবেক্ষণ","বিকল্প","পাঠান","JANUS-কে বার্তা","সব","চিন্তা","ইন্টারঅ্যাকশন","স্ন্যাপশট রিফ্রেশ করুন",
            "কোর","মেমরি","কার্যকলাপ","সিস্টেম অবস্থা","সামঞ্জস্য","গবেষণা কর্মক্ষেত্র","আর্টিফ্যাক্ট","পটভূমি গবেষণা",
            "রক্ষণাবেক্ষণ পর্যালোচনা","সেটিংস","অ্যাকাউন্ট","ভাষা","চেহারা","এই ডিভাইস থেকে সাইন আউট","সব ডিভাইস থেকে সাইন আউট",
            "অ্যাকাউন্ট মুছুন","বাতিল","বন্ধ করুন","← বিকল্প","রানটাইম কোর","স্থানীয় ও বৈশ্বিক JANUS লোড হচ্ছে…",
            "এই ডিভাইস · স্থানীয় JANUS","অনলাইন · বৈশ্বিক JANUS","এই স্ন্যাপশটে পর্যবেক্ষণযোগ্য কোর কার্যকলাপ নেই।","প্রযুক্তিগত বিবরণ");}
    private static Map<String,String> id(){return map(
            "Masuk","Buat akun","Lanjutkan dengan Google","Lupa kata sandi","Atur ulang kata sandi","Verifikasi / kirim ulang email",
            "Nama pengguna atau email","Kata sandi","Nama pengguna","Email","Menghubungkan ke JANUS…","Gagal masuk",
            "Obrolan","Pesan","Amati","Opsi","Kirim","Pesan untuk JANUS","Semua","Pikiran","Interaksi","Segarkan snapshot",
            "Inti","Memori","Aktivitas","Status sistem","Kompatibilitas","Ruang riset","Artefak","Riset latar belakang",
            "Tinjauan pemeliharaan","Pengaturan","Akun","Bahasa","Tampilan","Keluar dari perangkat ini","Keluar dari semua perangkat",
            "Hapus akun","Batal","Tutup","← Opsi","Inti runtime","Memuat JANUS lokal dan global…",
            "PERANGKAT INI · JANUS LOKAL","ONLINE · JANUS GLOBAL","Tidak ada aktivitas inti yang dapat diamati pada snapshot ini.","Detail teknis");}
    private static Map<String,String> vi(){return map(
            "Đăng nhập","Tạo tài khoản","Tiếp tục với Google","Quên mật khẩu","Đặt lại mật khẩu","Xác minh / gửi lại email",
            "Tên người dùng hoặc email","Mật khẩu","Tên người dùng","Email","Đang kết nối JANUS…","Đăng nhập thất bại",
            "Trò chuyện","Tin nhắn","Quan sát","Tùy chọn","Gửi","Nhắn JANUS","Tất cả","Suy nghĩ","Tương tác","Làm mới ảnh chụp",
            "Lõi","Bộ nhớ","Hoạt động","Trạng thái hệ thống","Tương thích","Không gian nghiên cứu","Hiện vật","Nghiên cứu nền",
            "Xem xét bảo trì","Cài đặt","Tài khoản","Ngôn ngữ","Giao diện","Đăng xuất thiết bị này","Đăng xuất tất cả thiết bị",
            "Xóa tài khoản","Hủy","Đóng","← Tùy chọn","Lõi thời gian chạy","Đang tải JANUS cục bộ và toàn cục…",
            "THIẾT BỊ NÀY · JANUS CỤC BỘ","TRỰC TUYẾN · JANUS TOÀN CỤC","Không có hoạt động lõi quan sát được trong ảnh chụp này.","Chi tiết kỹ thuật");}
    private static Map<String,String> th(){return map(
            "ลงชื่อเข้าใช้","สร้างบัญชี","ดำเนินการต่อด้วย Google","ลืมรหัสผ่าน","รีเซ็ตรหัสผ่าน","ยืนยัน / ส่งอีเมลอีกครั้ง",
            "ชื่อผู้ใช้หรืออีเมล","รหัสผ่าน","ชื่อผู้ใช้","อีเมล","กำลังเชื่อมต่อ JANUS…","ลงชื่อเข้าใช้ไม่สำเร็จ",
            "แชต","ข้อความ","สังเกต","ตัวเลือก","ส่ง","ข้อความถึง JANUS","ทั้งหมด","ความคิด","การโต้ตอบ","รีเฟรชภาพรวม",
            "คอร์","หน่วยความจำ","กิจกรรม","สถานะระบบ","ความเข้ากันได้","พื้นที่วิจัย","อาร์ติแฟกต์","วิจัยเบื้องหลัง",
            "ตรวจสอบการบำรุงรักษา","การตั้งค่า","บัญชี","ภาษา","ลักษณะที่ปรากฏ","ออกจากระบบอุปกรณ์นี้","ออกจากระบบทุกอุปกรณ์",
            "ลบบัญชี","ยกเลิก","ปิด","← ตัวเลือก","คอร์รันไทม์","กำลังโหลด JANUS ภายในและส่วนกลาง…",
            "อุปกรณ์นี้ · JANUS ภายใน","ออนไลน์ · JANUS ส่วนกลาง","ไม่มีการทำงานของคอร์ที่สังเกตได้ในภาพรวมนี้","รายละเอียดทางเทคนิค");}
    private static Map<String,String> ja(){return map(
            "サインイン","アカウントを作成","Google で続行","パスワードを忘れた","パスワードをリセット","メールを確認 / 再送信",
            "ユーザー名またはメール","パスワード","ユーザー名","メール","JANUS に接続中…","サインインに失敗しました",
            "チャット","メッセージ","観察","オプション","送信","JANUS にメッセージ","すべて","思考","やり取り","スナップショットを更新",
            "コア","メモリ","アクティビティ","システム状態","互換性","研究ワークスペース","成果物","バックグラウンド研究",
            "メンテナンス確認","設定","アカウント","言語","外観","この端末からサインアウト","すべての端末からサインアウト",
            "アカウントを削除","キャンセル","閉じる","← オプション","ランタイムコア","ローカルとグローバル JANUS を読み込み中…",
            "この端末 · ローカル JANUS","オンライン · グローバル JANUS","このスナップショットには観察可能なコア活動がありません。","技術詳細");}
    private static Map<String,String> ko(){return map(
            "로그인","계정 만들기","Google로 계속","비밀번호 찾기","비밀번호 재설정","이메일 확인 / 재전송",
            "사용자 이름 또는 이메일","비밀번호","사용자 이름","이메일","JANUS에 연결 중…","로그인 실패",
            "채팅","메시지","관찰","옵션","보내기","JANUS에게 메시지","전체","생각","상호작용","스냅샷 새로고침",
            "코어","메모리","활동","시스템 상태","호환성","연구 작업공간","아티팩트","백그라운드 연구",
            "유지보수 검토","설정","계정","언어","모양","이 기기에서 로그아웃","모든 기기에서 로그아웃",
            "계정 삭제","취소","닫기","← 옵션","런타임 코어","로컬 및 글로벌 JANUS 불러오는 중…",
            "이 기기 · 로컬 JANUS","온라인 · 글로벌 JANUS","이 스냅샷에는 관찰 가능한 코어 활동이 없습니다.","기술 세부정보");}
    private static Map<String,String> zhHans(){return map(
            "登录","创建账户","使用 Google 继续","忘记密码","重置密码","验证 / 重发邮件",
            "用户名或邮箱","密码","用户名","邮箱","正在连接 JANUS…","登录失败",
            "聊天","消息","观察","选项","发送","给 JANUS 发消息","全部","思考","交互","刷新快照",
            "核心","记忆","活动","系统状态","兼容性","研究工作区","成果文件","后台研究",
            "维护审查","设置","账户","语言","外观","退出此设备","退出所有设备",
            "删除账户","取消","关闭","← 选项","运行时核心","正在加载本地和全局 JANUS…",
            "此设备 · 本地 JANUS","在线 · 全局 JANUS","此快照中没有可观察的核心活动。","技术详情");}
    private static Map<String,String> zhHant(){return map(
            "登入","建立帳戶","使用 Google 繼續","忘記密碼","重設密碼","驗證 / 重寄郵件",
            "使用者名稱或電子郵件","密碼","使用者名稱","電子郵件","正在連線 JANUS…","登入失敗",
            "聊天","訊息","觀察","選項","傳送","傳訊息給 JANUS","全部","思考","互動","重新整理快照",
            "核心","記憶","活動","系統狀態","相容性","研究工作區","成果檔案","背景研究",
            "維護審查","設定","帳戶","語言","外觀","登出此裝置","登出所有裝置",
            "刪除帳戶","取消","關閉","← 選項","執行階段核心","正在載入本機與全域 JANUS…",
            "此裝置 · 本機 JANUS","線上 · 全域 JANUS","此快照中沒有可觀察的核心活動。","技術詳細資料");}
}
