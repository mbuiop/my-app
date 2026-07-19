// ============================================
// راه‌انداز چندسروری (Cluster) - سیستم چند-worker
// ============================================
// به‌جای «node server.js» (یک پروسه‌ی تنها)، با این فایل اجرا کن:
//
//     node cluster.js
//
// تا سیستم به تعداد هسته‌های CPU سرور (یا هر عددی که با WORKERS مشخص کنی)
// چند worker مستقل بالا بیاره که همه روی همون PORT به‌صورت لود-بالانس‌شده
// (round-robin، توسط خودِ Node.js) به درخواست‌ها جواب می‌دن.
//
// هر وقت خواستی تعداد سرورها/worker ها رو کم یا زیاد کنی، کافیه متغیر محیطی
// WORKERS رو عوض کنی و دوباره اجرا کنی، مثلاً:
//
//     WORKERS=8 node cluster.js
//
// اگه WORKERS ست نشه، به تعداد هسته‌های CPU همین سرور worker بالا میاد.
//
// نکته‌ی مهم: کارهای زمان‌بندی‌شده (مثل انتشار پست‌های scheduled تو server.js)
// با claim اتمیک روی دیتابیس (UPDATE ... WHERE is_published = 0) نوشته شدن،
// پس اجرای همزمانشون تو چند worker امنه - فقط یکیشون برنده‌ی هر ردیف می‌شه.
// ============================================
const cluster = require('cluster');
const os = require('os');

const WORKERS = Math.max(1, parseInt(process.env.WORKERS || '', 10) || os.cpus().length);

if (cluster.isPrimary || cluster.isMaster) {
    console.log(`🧩 حالت چندسروری فعال شد - در حال بالا آوردن ${WORKERS} worker (پردازنده‌های موجود: ${os.cpus().length})`);

    for (let i = 0; i < WORKERS; i++) {
        cluster.fork();
    }

    // اگه یه worker به هر دلیلی (کرش، خاموشی دستی و ...) از کار افتاد، خودکار یه worker جدید جاش بیار
    // بالا - این باعث می‌شه سیستم همیشه با همون تعداد worker که تنظیم کردی سرپا بمونه.
    cluster.on('exit', (worker, code, signal) => {
        console.error(`⚠️ worker با pid ${worker.process.pid} از کار افتاد (کد=${code}, سیگنال=${signal}) - یه worker جدید بالا میاد`);
        cluster.fork();
    });

    cluster.on('online', (worker) => {
        console.log(`✅ worker جدید با pid ${worker.process.pid} آنلاین شد`);
    });

    // خاموشی مرتب کل سیستم چندسروری وقتی پروسه‌ی اصلی سیگنال خاموشی می‌گیره
    const shutdown = () => {
        console.log('🛑 در حال خاموش کردن مرتب همه‌ی worker ها...');
        for (const id in cluster.workers) {
            cluster.workers[id].process.kill('SIGTERM');
        }
        setTimeout(() => process.exit(0), 12000).unref();
    };
    process.on('SIGTERM', shutdown);
    process.on('SIGINT', shutdown);
} else {
    // هر worker دقیقاً همون سرور اصلی (server.js) رو با تمام قابلیت‌هاش اجرا می‌کنه -
    // هیچ تغییری تو کد سرور لازم نیست، چون Node.js خودش listen() هر worker رو
    // پشت پروسه‌ی اصلی به‌صورت شفاف لود-بالانس می‌کنه.
    require('./server.js');
}
