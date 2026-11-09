"""
=============================================================================
Project: CSIT Batch 8 Academic Library Telegram Bot
Description: Advanced moderated academic repository bot supporting dual-path 
             uploads (Student Moderated Submissions vs. Password-Protected 
             Admin/Contributor Direct Publishing).
Author: Mohamed Al-Zulaimi
Version: 2.1.2 (Production Ready)
=============================================================================
"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- إعدادات المصادقة والاتصال الأساسية ---
TELEGRAM_BOT_TOKEN = "9022187543:AAElP4LB9NRYa62mElWOrbl8Dol6MWlNfKA"

# المعرف الرقمي للمشرف الرئيسي لاستقبال طلبات الاعتماد والاستفسارات
ADMINISTRATOR_ID = "m_1559"  # استبدل هذا الرقم بمعرف تليجرام الخاص بك (Telegram User ID)

# كلمة السر الخاصة بالمناديب والطلاب الموثوقين للنشر الفوري
ADMIN_SECRET_PASSWORD = "csit.1559.com"

# تهيئة التخزين المؤقت وحالات الماكينة (FSM)
storage = MemoryStorage()
dispatcher = Dispatcher(storage=storage)

# مستودع البيانات الأكاديمي لتخزين الملازم والمقاطع المعتمدة
ACADEMIC_REPOSITORY = {
    "prog": {"theory": [], "practical": []},
    "mining": {"theory": [], "practical": []},
    "analysis": {"theory": [], "practical": []},
    "web": {"theory": [], "practical": []},
    "theory": {"theory": [], "practical": []},
    "graphics": {"theory": [], "practical": []},
}

# --- تعريف حالات النظام (FSM States) ---
class SubmissionStates(StatesGroup):
    awaiting_document = State()
    selecting_subject = State()
    selecting_branch = State()
    choosing_upload_path = State()
    awaiting_admin_password = State()

class SupportStates(StatesGroup):
    awaiting_inquiry = State()

class AdministrationStates(StatesGroup):
    awaiting_response_text = State()

# فهرس المقررات الدراسية للمستوى الثالث
CURRICULUM_SUBJECTS = {
    "prog": "💻 برمجة متقدمة",
    "mining": "📊 تنقيب بيانات",
    "analysis": "📐 تحليل وتصميم نظم",
    "web": "🌐 تقنيات ويب متقدمة",
    "theory": "🧮 نظرية احتسابية",
    "graphics": "🎨 رسم بالحاسوب"
}

# --- هندسة واجهات المستخدم التفاعلية (UI Keyboards) ---

def generate_main_menu() -> InlineKeyboardMarkup:
    """توليد لوحة المفاتيح الرئيسية للنظام الأكاديمي."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 المقرر الدراسي الرسمي", callback_data="subjects_menu")],
        [InlineKeyboardButton(text="📤 مشاركة الزملاء (ملخصات الطلاب)", callback_data="shared_menu")],
        [InlineKeyboardButton(text="💬 الاستفسارات والشكاوى (تواصل أكاديمي)", callback_data="support_start")],
        [InlineKeyboardButton(text="📢 قناة الدفعة والتعاميم الرسمية", url="https://t.me/your_channel")],
        [InlineKeyboardButton(text="ℹ️ حول النظام الأكاديمي", callback_data="about_system")]
    ])

def generate_collaboration_menu() -> InlineKeyboardMarkup:
    """توليد خيارات قسم مساهمات الطلاب."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 رفع ملزمة أو مرجع جديد", callback_data="start_upload")],
        [InlineKeyboardButton(text="📂 مستودع ملخصات الدفعة الثامنة", callback_data="browse_shared")],
        [InlineKeyboardButton(text="⬅️ العودة للقائمة الرئيسية", callback_data="main_menu")]
    ])

def generate_subjects_keyboard(callback_prefix: str = "subj") -> InlineKeyboardMarkup:
    """توليد قائمة المواد الدراسية ديناميكياً."""
    buttons = []
    for code, title in CURRICULUM_SUBJECTS.items():
        buttons.append([InlineKeyboardButton(text=title, callback_data=f"{callback_prefix}_{code}")])
    buttons.append([InlineKeyboardButton(text="⬅️ العودة", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def generate_branch_keyboard(subject_code: str, callback_prefix: str = "branch") -> InlineKeyboardMarkup:
    """توليد خيارات الفروع الأكاديمية (نظري / عملي)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 القسم النظري", callback_data=f"{callback_prefix}_{subject_code}_theory")],
        [InlineKeyboardButton(text="💻 القسم العملي", callback_data=f"{callback_prefix}_{subject_code}_practical")],
        [InlineKeyboardButton(text="⬅️ العودة للمواد", callback_data="back_to_subjects")]
    ])

# --- معالجات الأحداث والمسارات الأساسية ---

@dispatcher.message(CommandStart())
async def handle_start_command(message: Message, state: FSMContext) -> None:
    """معالجة أمر البدء وترحيب المستخدم بالنظام."""
    await state.clear()
    student_name = message.from_user.first_name
    greeting_message = (
        f"مرحباً بك يا {html.bold(student_name)} في نظام 🤖 {html.italic('مكتبة الدفعة الثامنة CSIT')}\n\n"
        "البوابة الأكاديمية المركزية لتنظيم الملازم، المقررات، ومشاركات الطلاب.\n"
        "يرجى تحديد الخيار المطلوب من القائمة أدناه:"
    )
    await message.answer(greeting_message, reply_markup=generate_main_menu(), parse_mode=ParseMode.HTML)

@dispatcher.callback_query(F.data == "main_menu")
async def handle_main_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """إعادة توجيه المستخدم إلى القائمة الرئيسية وتصفح الحالة."""
    await state.clear()
    await callback.message.edit_text(
        "القائمة الرئيسية - النظام الأكاديمي للدفعة الثامنة:",
        reply_markup=generate_main_menu()
    )
    await callback.answer()

@dispatcher.callback_query(F.data == "subjects_menu")
async def handle_subjects_menu_callback(callback: CallbackQuery) -> None:
    """عرض قائمة المقررات الدراسية الرسمية."""
    await callback.message.edit_text(
        "اختر المقرر الدراسي المطلوب للتصفح:",
        reply_markup=generate_subjects_keyboard("subj")
    )
    await callback.answer()

@dispatcher.callback_query(F.data == "back_to_subjects")
async def handle_back_to_subjects_callback(callback: CallbackQuery) -> None:
    """الرجوع إلى قائمة المواد الدراسية."""
    await callback.message.edit_text(
        "اختر المقرر الدراسي المطلوب:",
        reply_markup=generate_subjects_keyboard("subj")
    )
    await callback.answer()

# --- إدارة مساهمات ومشاركات الطلاب (مسار مزدوج) ---

@dispatcher.callback_query(F.data == "shared_menu")
async def handle_shared_menu_callback(callback: CallbackQuery) -> None:
    """عرض لوحة تحكم مشاركات الزملاء."""
    await callback.message.edit_text(
        "📤 <b>قسم مساهمات وملخصات الزملاء</b>\n\n"
        "يمكنك رفع الملفات للمراجعة العامة، أو استخدام كلمة السر الخاصة بالمشرفين للنشر الفوري.",
        reply_markup=generate_collaboration_menu(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dispatcher.callback_query(F.data == "start_upload")
async def handle_start_upload_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """بدء إجراءات رفع ملف جديد من قِبل الطالب."""
    await callback.message.edit_text(
        "📥 <b>رفع مادة أكاديمية جديدة</b>\n\n"
        "يرجى إرسال الملف المستهدف (PDF، مستند، أو وسائط) لمشاركته:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء العملية", callback_data="shared_menu")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(SubmissionStates.awaiting_document)
    await callback.answer()

@dispatcher.message(SubmissionStates.awaiting_document, F.document | F.photo | F.video)
async def handle_document_reception(message: Message, state: FSMContext) -> None:
    """استلام الملف المؤقت وتخزين خصائصه في الذاكرة."""
    if message.document:
        file_identifier = message.document.file_id
        document_name = message.document.file_name or "ملف_أكاديمي_بدون_عنوان"
    elif message.photo:
        file_identifier = message.photo[-1].file_id
        document_name = "مستند_صورة_توضيحية"
    else:
        file_identifier = message.video.file_id
        document_name = "محتوى_مرئي_تعليمي"

    await state.update_data(file_id=file_identifier, file_name=document_name)
    await state.set_state(SubmissionStates.selecting_subject)
    
    await message.answer(
        "✅ تم استلام الملف بنجاح.\nالرجاء تحديد المقرر الدراسي المرتبط به:",
        reply_markup=generate_subjects_keyboard("up_subj")
    )

@dispatcher.callback_query(SubmissionStates.selecting_subject, F.data.startswith("up_subj_"))
async def handle_upload_subject_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """تحديد المقرر الدراسي للملف المرفوع."""
    subject_code = callback.data.split("_")[2]
    await state.update_data(subject_code=subject_code)
    await state.set_state(SubmissionStates.selecting_branch)
    
    await callback.message.edit_text(
        f"المقرر المختار: <b>{CURRICULUM_SUBJECTS.get(subject_code)}</b>\n\nهل يتبع هذا الملف القسم النظري أم العملي؟",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 القسم النظري", callback_data="up_branch_theory")],
            [InlineKeyboardButton(text="💻 القسم العملي", callback_data="up_branch_practical")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="shared_menu")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dispatcher.callback_query(SubmissionStates.selecting_branch, F.data.startswith("up_branch_"))
async def handle_branch_selection_for_upload(callback: CallbackQuery, state: FSMContext) -> None:
    """تخزين القسم واختيار مسار الرفع النهائي (طلاب مشاركون vs مشرفون بكلمة سر)."""
    branch_type = callback.data.split("_")[2]
    await state.update_data(branch_type=branch_type)
    await state.set_state(SubmissionStates.choosing_upload_path)
    
    branch_label = "النظري" if branch_type == "theory" else "العملي"
    session_data = await state.get_data()
    subject_title = CURRICULUM_SUBJECTS.get(session_data.get("subject_code"))

    upload_paths_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 رفع عبر مسار طلاب الدفعة (للمراجعة)", callback_data="path_student_review")],
        [InlineKeyboardButton(text="🔑 رفع عبر مسار المشرفين (كلمة السر)", callback_data="path_admin_password")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="shared_menu")]
    ])

    await callback.message.edit_text(
        f"📁 المقرر: <b>{subject_title} ({branch_label})</b>\n\n"
        "الرجاء اختيار طريقة النشر المستهدفة:",
        reply_markup=upload_paths_keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# --- المسار الأول: رفع الطلاب (يحتاج موافقة المشرف) ---
@dispatcher.callback_query(SubmissionStates.choosing_upload_path, F.data == "path_student_review")
async def process_student_review_path(callback: CallbackQuery, state: FSMContext) -> None:
    """إرسال الملف إلى المشرف للمراجعة والاعتماد."""
    session_data = await state.get_data()
    subject_code = session_data.get("subject_code")
    branch_type = session_data.get("branch_type")
    file_identifier = session_data.get("file_id")
    document_name = session_data.get("file_name")
    user_entity = callback.from_user
    
    await state.clear()
    branch_label = "النظري" if branch_type == "theory" else "العملي"
    subject_title = CURRICULUM_SUBJECTS.get(subject_code)

    admin_approval_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة ونشر", callback_data=f"approve_{user_entity.id}_{subject_code}_{branch_type}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_{user_entity.id}")
        ]
    ])
    
    await callback.bot.send_document(
        chat_id=ADMINISTRATOR_ID,
        document=file_identifier,
        caption=f"🔔 <b>طلب مراجعة ملف أكاديمي (مسار الطلاب):</b>\n\n"
                f"👤 الطالب: {user_entity.full_name} (@{user_entity.username or 'بدون معرف'})\n"
                f"📁 اسم الملف: {document_name}\n"
                f"📚 المقرر: {subject_title} ({branch_label})",
        reply_markup=admin_approval_keyboard,
        parse_mode=ParseMode.HTML
    )
    
    pending_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        "⏳ <b>تم إرسال الملف بنجاح إلى الإدارة الأكاديمية للمراجعة.</b>\n\n"
        "سيتم إدراج الملف في مستودع الدفعة فور اعتماده رسمياً.",
        reply_markup=pending_keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# --- المسار الثاني: رفع المشرفين (كلمة السر) ---
@dispatcher.callback_query(SubmissionStates.choosing_upload_path, F.data == "path_admin_password")
async def process_admin_password_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """طلب إدخال كلمة سر المشرفين للمتابعة."""
    await state.set_state(SubmissionStates.awaiting_admin_password)
    await callback.message.edit_text(
        "🔑 <b>التحقق من صلاحيات المشرف</b>\n\n"
        "الرجاء إدخال كلمة السر الخاصة بالمشرفين والمناديب لإتمام النشر الفوري:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="shared_menu")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dispatcher.message(SubmissionStates.awaiting_admin_password)
async def verify_admin_password_and_publish(message: Message, state: FSMContext) -> None:
    """التحقق من صحة كلمة السر ونشر الملف فوراً إن كانت مطابقة."""
    entered_password = message.text.strip()
    session_data = await state.get_data()
    
    subject_code = session_data.get("subject_code")
    branch_type = session_data.get("branch_type")
    file_identifier = session_data.get("file_id")
    document_name = session_data.get("file_name")
    user_entity = message.from_user

    if entered_password == ADMIN_SECRET_PASSWORD:
        ACADEMIC_REPOSITORY[subject_code][branch_type].append({
            "name": document_name,
            "file_id": file_identifier,
            "sender": f"مشرف معتمد ({user_entity.first_name})"
        })
        await state.clear()
        
        success_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 رفع ملف آخر", callback_data="start_upload")],
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
        ])
        await message.answer(
            f"🎉 <b>تم التحقق بنجاح ونشر الملف فوراً!</b>\n\n"
            f"📁 الملف: `{document_name}`\n📚 المقرر: {CURRICULUM_SUBJECTS.get(subject_code)}",
            reply_markup=success_keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        error_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 إعادة المحاولة", callback_data="path_admin_password")],
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
        ])
        await message.answer(
            "❌ <b>كلمة السر غير صحيحة!</b>\n\nيرجى التأكد من الرمز وإعادة المحاولة.",
            reply_markup=error_keyboard,
            parse_mode=ParseMode.HTML
        )

# --- إدارة موافقة المشرف على مسار الطلاب ---

@dispatcher.callback_query(F.data.startswith("approve_"))
async def process_admin_approval(callback: CallbackQuery) -> None:
    """قبول المشرف للملف المرفوع عبر مسار الطلاب ونشره رسمياً."""
    query_parts = callback.data.split("_")
    student_telegram_id = int(query_parts[1])
    subject_code = query_parts[2]
    branch_type = query_parts[3]
    
    current_message = callback.message
    original_caption = current_message.caption
    file_identifier = current_message.document.file_id
    document_name = current_message.document.file_name or "ملف_أكاديمي"
    
    ACADEMIC_REPOSITORY[subject_code][branch_type].append({
        "name": document_name,
        "file_id": file_identifier,
        "sender": "طالب مساهم"
    })
    
    await current_message.edit_caption(
        caption=f"{original_caption}\n\n✅ **حالة الاعتمـاد: تمت الموافقة ونشر المحتوى بنجاح.**",
        parse_mode=ParseMode.HTML
    )
    
    try:
        await callback.bot.send_message(
            chat_id=student_telegram_id,
            text=f"🎉 تهانينا! قامت الإدارة الأكاديمية بالموافقة على نشر ملفك ({document_name}) في مستودع الدفعة."
        )
    except Exception:
        pass
    
    await callback.answer("تمت الموافقة ونشر الملف بنجاح.")

@dispatcher.callback_query(F.data.startswith("reject_"))
async def process_admin_rejection(callback: CallbackQuery) -> None:
    """رفض المشرف للملف المرفوع عبر مسار الطلاب."""
    query_parts = callback.data.split("_")
    student_telegram_id = int(query_parts[1])
    
    current_message = callback.message
    await current_message.edit_caption(
        caption=f"{current_message.caption}\n\n❌ **حالة الاعتمـاد: تم رفض الملف ولم يتم إدراجه بالمستودع.**",
        parse_mode=ParseMode.HTML
    )
    
    try:
        await callback.bot.send_message(
            chat_id=student_telegram_id,
            text="⚠️ عذراً، اعتذرت الإدارة الأكاديمية عن نشر الملف المرسل لعدم استيفائه المعايير المطلوبة."
        )
    except Exception:
        pass
    
    await callback.answer("تم رفض الملف.")

# --- استعراض مستودع ملخصات الدفعة ---

@dispatcher.callback_query(F.data == "browse_shared")
async def browse_repository_subjects(callback: CallbackQuery) -> None:
    """عرض قائمة المواد المتاحة للاستعراض."""
    await callback.message.edit_text(
        "📂 <b>مستودع ملخصات وملازم الزملاء المعتمدة</b>\n\nيرجى اختيار المقرر الدراسي المناسب:",
        reply_markup=generate_subjects_keyboard("browse_subj"),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dispatcher.callback_query(F.data.startswith("browse_subj_"))
async def browse_repository_branches(callback: CallbackQuery) -> None:
    """اختيار القسم (نظري/عملي) لاستعراض الملفات."""
    subject_code = callback.data.split("_")[2]
    await callback.message.edit_text(
        f"📚 <b>{CURRICULUM_SUBJECTS.get(subject_code)}</b>\n\nيرجى تحديد القسم الأكاديمي:",
        reply_markup=generate_branch_keyboard(subject_code, "browse_branch"),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dispatcher.callback_query(F.data.startswith("browse_branch_"))
async def render_repository_files_list(callback: CallbackQuery) -> None:
    """جلب وإرسال كافة الملفات المعتمدة المرتبطة بالقسم المحدد."""
    query_segments = callback.data.split("_")
    subject_code = query_segments[2]
    branch_type = query_segments[3]
    
    target_files_collection = ACADEMIC_REPOSITORY[subject_code][branch_type]
    branch_label = "النظري" if branch_type == "theory" else "العملي"
    subject_title = CURRICULUM_SUBJECTS.get(subject_code)
    
    if not target_files_collection:
        fallback_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ رجوع للمستودع", callback_data="browse_shared")]
        ])
        await callback.message.edit_text(
            f"📁 <b>{subject_title}</b> ({branch_label})\n\nعذراً، لا توجد ملفات معتمدة في هذا القسم حتى اللحظة.",
            reply_markup=fallback_keyboard,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📁 <b>محتويات مستودع {subject_title} ({branch_label}):</b>\nجاري إرسال الملفات المتاحة الآن 👇",
        parse_mode=ParseMode.HTML
    )
    
    for record in target_files_collection:
        file_caption = f"📄 <b>{record['name']}</b>\n👤 المساهم: {record['sender']}"
        await callback.message.answer_document(document=record["file_id"], caption=file_caption, parse_mode=ParseMode.HTML)
    
    return_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 العودة للمستودع", callback_data="browse_shared")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    await callback.message.answer("تم عرض كافة الملفات المعتمدة في هذا القسم بنجاح ✅", reply_markup=return_keyboard)
    await callback.answer()

# --- نظام الاستفسارات والشكاوى الأكاديمية (Support System) ---

@dispatcher.callback_query(F.data == "support_start")
async def initialize_support_ticket(callback: CallbackQuery, state: FSMContext) -> None:
    """بدء جلسة إرسال استفسار أو شكوى للمشرف."""
    await callback.message.edit_text(
        "💬 <b>قسم الاستفسارات والتواصل الأكاديمي</b>\n\n"
        "يرجى كتابة نص الاستفسار أو الملاحظة بوضوح، وسيتم توجيهها مباشرة إلى إدارة النظام:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="main_menu")]
        ]),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(SupportStates.awaiting_inquiry)
    await callback.answer()

@dispatcher.message(SupportStates.awaiting_inquiry)
async def dispatch_inquiry_to_admin(message: Message, state: FSMContext) -> None:
    """إرسال تذكرة الاستفسار مباشرة إلى لوحة تحكم المشرف."""
    user_entity = message.from_user
    inquiry_text = message.text
    await state.clear()
    
    admin_response_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ الرد على الطالب", callback_data=f"reply_student_{user_entity.id}")]
    ])
    
    await message.bot.send_message(
        chat_id=ADMINISTRATOR_ID,
        text=f"📩 <b>استفسار أكاديمي جديد:</b>\n\n"
             f"👤 الطالب: {user_entity.full_name} (@{user_entity.username or 'بدون معرف'})\n"
             f"🆔 المعرف الرقمي: `{user_entity.id}`\n\n"
             f"💬 النص الوارد:\n{inquiry_text}",
        reply_markup=admin_response_keyboard,
        parse_mode=ParseMode.HTML
    )
    
    await message.answer(
        "✅ **تم إرسال استفسارك إلى إدارة النظام بنجاح.**\nسيتم الرد في أقرب وقت ممكن.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
        ])
    )

@dispatcher.callback_query(F.data.startswith("reply_student_"))
async def prompt_admin_response_input(callback: CallbackQuery, state: FSMContext) -> None:
    """تفعيل وضع إدخال رد المشرف الموجه للطالب."""
    student_telegram_id = int(callback.data.split("_")[2])
    await state.update_data(target_student_id=student_telegram_id)
    await state.set_state(AdministrationStates.awaiting_response_text)
    
    await callback.message.answer(
        "✍️ يرجى كتابة نص الرد الرسمي الموجه للطالب أدناه:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@dispatcher.message(AdministrationStates.awaiting_response_text, F.from_user.id == ADMINISTRATOR_ID)
async def dispatch_admin_response_to_student(message: Message, state: FSMContext) -> None:
    """إرسال رد المشرف مباشرة إلى حساب الطالب المستهدف."""
    session_parameters = await state.get_data()
    student_telegram_id = session_parameters.get("target_student_id")
    response_content = message.text
    await state.clear()
    
    try:
        await message.bot.send_message(
            chat_id=student_telegram_id,
            text=f"📥 <b>رد رسمي من إدارة النظام الأكاديمي:</b>\n\n{response_content}",
            parse_mode=ParseMode.HTML
        )
        await message.answer("✅ تم إرسال الرد إلى الطالب بنجاح.")
    except Exception as execution_error:
        await message.answer(f"❌ تعذر إرسال الرد بسبب خطأ تقني: {execution_error}")

@dispatcher.callback_query(F.data == "about_system")
async def render_system_metadata(callback: CallbackQuery) -> None:
    """عرض معلومات النظام الأكاديمي وتفاصيل المطور."""
    return_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ العودة", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        "🤖 <b>نظام مكتبة الدفعة الثامنة CSIT</b>\n\n"
        "منصة برمجية متكاملة لخدمة طلاب المستوى الثالث، تهدف إلى تنظيم المراجع، الملازم، والمقررات الدراسية بدقة واحترافية.\n\n"
        "تصميم وتطوير: محمد الظليمي.",
        reply_markup=return_button,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# --- حلقة التشغيل الرئيسية (Main Execution Loop) ---

async def main_application_loop() -> None:
    """تهيئة وتشغيل حلقة الاتصال الخاصة بخدمة البوت (Polling)."""
    bot_instance = Bot(
        token=TELEGRAM_BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    await bot_instance.delete_webhook(drop_pending_updates=True)
    print("Academic Telegram Bot initialized successfully and running...")
    await dispatcher.start_polling(bot_instance)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main_application_loop())
    except (KeyboardInterrupt, SystemExit):
        print("Bot execution safely terminated.")