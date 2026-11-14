"""
backend-poc-technical/test_red_flags_round4.py

Verification suite for Part F3 (Red Flags Round 4):
1. F3.a Regression:
   - Single vomit followed by drinking normally ('ek baar ulti hui, ab paani pee raha hoon') is NOT Red.
   - Intractable / repeated vomiting ('bar bar ulti', 'throwing up everything', 'paani bhi nahi ruk raha') IS Red.
2. F3.b Failure Verbs & Family Subjects:
   - Full sentences with family subjects ('dadi ammi', 'abba ki', 'my father', Urdu 'نانی'),
     in present/perfect/respect forms for all failure verbs.
3. F3.c Missing Word Types:
   - Unresponsive: be-sudh / بے سدھ, found on the floor, out unknown time + drowsy.
   - Breathing: hawa andar nahi jaati, bilkul ukhri hui, wheezing + blue lips, lait nahi sakta / can't lie down.
   - Chest: seene ke beech dabav + ulti jaisa/nausea, someone sitting/standing on my chest.
   - Stroke: ajeeb baatein + limb won't move, aadha chehra latka + speech/comprehension.
4. F3.d Unseen Evaluation:
   - 20 fresh positives and 20 fresh negatives written in an independent voice.
"""

import pytest
from agents.red_flag_patterns import match, match_categories


# =============================================================================
# F3.a: Regression Tests (Single Vomit Recovery vs Intractable Fluids)
# =============================================================================

@pytest.mark.parametrize("benign_text", [
    "ek baar ulti hui, ab paani pee raha hoon",
    "ek baar ulti hui thi subah",
    "aik bar qay aayi thi, ab theek hoon pani pee raha hoon",
    "threw up once this morning, able to drink water fine now",
    "had one vomit earlier, tolerating fluids well now",
    "vomited once after eating something spicy, drinking water normally now",
    "ایک بار الٹی ہوئی تھی، اب پانی پی رہا ہوں",
    "ایک دفعہ قے آئی تھی لیکن اب پانی ٹھیک سے پی رہے ہیں",
    "sirf ek dafa ulti hui thi, ab paani pee raha hai",
])
def test_f3a_single_vomit_with_recovery_is_not_red(benign_text: str):
    hit, cat = match(benign_text)
    assert hit is False, f"Expected False for single/recovered vomit '{benign_text}', got {cat}"


@pytest.mark.parametrize("emergency_text", [
    "paani bhi nahi ruk raha",
    "ek ghoont bhi wapas nikal jata hai",
    "bar bar ulti ho rahi hai",
    "throwing up continuously for hours, keep nothing down",
    "vomiting nonstop since morning and cannot keep water down",
    "musalsal ultiyan aa rahi hain",
    "har cheez ulti ho rahi hai jo bhi khaye ya peeye",
    "پانی بھی نہیں رک رہا اور مسلسل الٹیاں ہیں",
    "ایک گھونٹ بھی واپس نکل جاتا ہے کچھ نہیں رک رہا",
    "مسلسل قے ہو رہی ہے پانی بھی نہیں ٹھہر رہا",
])
def test_f3a_intractable_fluids_and_repeated_vomiting_is_red(emergency_text: str):
    hit, cat = match(emergency_text)
    assert hit is True, f"Expected Red emergency for '{emergency_text}'"
    assert cat == "dka_vomiting_high_glucose", f"Expected dka_vomiting_high_glucose, got {cat}"


# =============================================================================
# F3.b: Failure Verbs in Full Sentences with Family Subjects & Respect Forms
# =============================================================================

FAMILY_FAILURE_VERB_CASES = [
    # Loss of consciousness / Eye opening
    ("dadi ammi aankhein nahi khol rahi hain", "loss_of_consciousness"),
    ("dadi jaan aankhein nahi khul rahin aur hosh nahi hai", "loss_of_consciousness"),
    ("my father cannot open his eyes and is not waking up", "loss_of_consciousness"),
    ("my mother won't open her eyes and is completely unresponsive", "loss_of_consciousness"),
    ("نانی اماں آنکھیں نہیں کھول رہی ہیں", "loss_of_consciousness"),
    ("دادا جی کی آنکھیں نہیں کھل رہیں اور جواب نہیں دے رہے", "loss_of_consciousness"),
    ("walid sahab aankh nahi khol rahe", "loss_of_consciousness"),

    # Breathing failure
    ("abba ko hawa andar nahi jaati", "breathing"),
    ("ammi ko hawa andar nahi ja rahi, dam ghut raha hai", "breathing"),
    ("my father says no air is going in when he tries to breathe", "breathing"),
    ("my mother feels like air isn't going in and she is choking", "breathing"),
    ("نانی جان کو ہوا اندر نہیں جا رہی", "breathing"),
    ("امی جان کہتی ہیں ہوا اندر نہیں جاتی اور دم گھٹتا ہے", "breathing"),
    ("dadi ammi ko saans bilkul nahi aa rahi", "breathing"),
    ("abba jaan ko saans bilkul nahi aa rahi hai", "breathing"),

    # Motor / Limb failure
    ("walida ka haath hila nahi pa rahi hain", "confusion_and_stroke"),
    ("dadi ammi ka haath hil nahi raha", "confusion_and_stroke"),
    ("abba ka pair kaam nahi kar raha", "confusion_and_stroke"),
    ("walid sahab ki taang kaam nahi kar rahi", "confusion_and_stroke"),
    ("my father cannot move his left arm at all", "confusion_and_stroke"),
    ("my mother's right leg is not working and she cannot lift it", "confusion_and_stroke"),
    ("دادا جان کا بازو ہل نہیں رہا", "confusion_and_stroke"),
    ("نانا کا پاؤں کام نہیں کر رہا", "confusion_and_stroke"),
    ("امی جان اپنا سیدھا ہاتھ نہیں ہلا پا رہیں", "confusion_and_stroke"),
    ("chacha ka bazu uth nahi raha bilkul bejan hai", "confusion_and_stroke"),

    # Speech / Comprehension failure
    ("dadi ko baat samajh nahi aa rahi", "confusion_and_stroke"),
    ("walida ko hamari baat samajh nahi aa rahi aur zaban ruk rahi hai", "confusion_and_stroke"),
    ("my grandmother cannot understand words we are saying", "confusion_and_stroke"),
    ("father's words are not making sense and he cannot speak properly", "confusion_and_stroke"),
    ("دادی جان کو بات سمجھ نہیں آ رہی", "confusion_and_stroke"),
    ("والد صاحب بول نہیں پا رہے اور الفاظ گڈ مڈ ہو گئے ہیں", "confusion_and_stroke"),
    ("nanijan bol nahi pa rahi hain bilkul awaz band ho gayi hai", "confusion_and_stroke"),
]

@pytest.mark.parametrize("text,expected_category", FAMILY_FAILURE_VERB_CASES)
def test_f3b_failure_verbs_with_family_subjects(text: str, expected_category: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect emergency for '{text}'"
    assert cat == expected_category, f"Wrong category for '{text}': expected {expected_category}, got {cat}"


# =============================================================================
# F3.c: Missing Word Types
# =============================================================================

@pytest.mark.parametrize("text,expected_cat", [
    # Unresponsive: be-sudh, found on floor, out unknown time + drowsy
    ("dadi jaan subah se be-sudh pari hain", "loss_of_consciousness"),
    ("walid sahab be-sudh pare hain aur pukarne par nahi uth rahe", "loss_of_consciousness"),
    ("بے سدھ پڑے ہیں اور کوئی جواب نہیں دے رہے", "loss_of_consciousness"),
    ("mother was found on the floor unresponsive", "loss_of_consciousness"),
    ("my father was found on floor and is completely drowsy and out", "loss_of_consciousness"),
    ("walid sahab farsh par pare mile aur hosh nahi tha", "loss_of_consciousness"),
    ("فرش پر پڑا ملا اور ہوش نہیں تھا", "loss_of_consciousness"),
    ("dont know how long i was out and feeling extremely drowsy", "loss_of_consciousness"),
    ("do not know how long out, very confused and drowsy", "loss_of_consciousness"),

    # Breathing: hawa andar nahi jaati, bilkul ukhri hui, wheezing + blue lips, lait nahi sakta
    ("hawa andar nahi jaati, saans phans rahi hai", "breathing"),
    ("ہوا اندر نہیں جاتی", "breathing"),
    ("dadi ki saans bilkul ukhri hui hai", "breathing"),
    ("bilkul ukhri hui saans hai aur bolna mushkil hai", "breathing"),
    ("سانس بالکل اکھڑی ہوئی ہے", "breathing"),
    ("bhai is wheezing badly and has blue lips", "breathing"),
    ("audible wheezing with bluish lips", "breathing"),
    ("seeti jaisi awaz hai aur hont neelay ho gaye hain", "breathing"),
    ("سیٹی جیسی آواز ہے اور نیلے ہونٹ ہو گئے ہیں", "breathing"),
    ("abba jaan lait nahi sakte, dam ghutne lagta hai", "breathing"),
    ("patient cannot lie flat due to severe shortness of breath", "breathing"),
    ("cant lie down flat without suffocating", "breathing"),
    ("سیدھا لیٹنا ممکن نہیں ہے دم گھٹتا ہے", "breathing"),

    # Chest: seene ke beech dabav + ulti jaisa/nausea, someone sitting/standing on chest
    ("seene ke beech dabav hai aur ulti jaisa lag raha hai", "chest_pain"),
    ("darmiyan e seena me dabav aur matli ho rahi hai", "chest_pain"),
    ("severe pressure in middle of chest and feeling like vomiting", "chest_pain"),
    ("سینے کے بیچ دباؤ ہے اور متلی ہو رہی ہے", "chest_pain"),
    ("feels like someone is sitting on my chest", "chest_pain"),
    ("someone standing on my chest, unbearable heaviness", "chest_pain"),
    ("seene par koi betha hai aesa lagta hai", "chest_pain"),
    ("seenay pe koi khara hai bojh se dam ghut raha hai", "chest_pain"),
    ("سینے پر کوئی بیٹھا ہے شدید بوجھ ہے", "chest_pain"),

    # Stroke: ajeeb baatein + limb won't move, aadha chehra latka + speech/comprehension
    ("dada ji ajeeb baatein kar rahe hain aur bazu hil nahi raha", "confusion_and_stroke"),
    ("talking strange words and cannot move left arm", "confusion_and_stroke"),
    ("عجیب باتیں کر رہے ہیں اور ہاتھ نہیں ہل رہا", "confusion_and_stroke"),
    ("chachi ka aadha chehra latka hua hai aur baat nahi bol pa rahe", "confusion_and_stroke"),
    ("half face drooping and speech is completely slurred", "confusion_and_stroke"),
    ("chehra ek taraf latak gaya aur hamari baat samajh nahi aa rahi", "confusion_and_stroke"),
    ("آدھا چہرہ لٹک گیا اور بات سمجھ نہیں آ رہی", "confusion_and_stroke"),
])
def test_f3c_missing_word_types(text: str, expected_cat: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect missing word type for '{text}'"
    assert cat == expected_cat, f"Wrong category for '{text}': expected {expected_cat}, got {cat}"


# =============================================================================
# F3.d: 20 Unseen Positives & 20 Unseen Negatives (Independent Voice)
# =============================================================================

UNSEEN_20_POSITIVES = [
    ("chachi subah se be-sudh hain, pukarne par bhi jawab nahi de rahin", "loss_of_consciousness"),
    ("dada ji ka aadha chehra achanak latak gaya aur alfaaz samajh nahi aa rahe", "confusion_and_stroke"),
    ("ammi bol rahi hain hawa bilkul andar nahi jaati, gale me phanda sa lagta hai", "breathing"),
    ("abba let nahi pa rahe, bistar par lette hi dam ghutne lagta hai", "breathing"),
    ("bhai ko lag raha hai koi seenay pe khara ho gaya hai, shadeed dabao hai", "chest_pain"),
    ("darmiyan e seena me sakht dabav hai aur baar baar ulti jaisa dil kharab ho raha hai", "chest_pain"),
    ("phuppo ki daayi taang kaam nahi kar rahi, chalna to door hilaya bhi nahi ja raha", "confusion_and_stroke"),
    ("nanijan ko kuch samajh nahi aa rahe hum kya keh rahe hain aur zaban ruk rahi hai", "confusion_and_stroke"),
    ("mother collapsed on the kitchen floor, still unconscious after 10 minutes", "loss_of_consciousness"),
    ("father feels an intolerable vice crushing the middle of his chest with severe nausea", "chest_pain"),
    ("patient cannot lie flat on the exam table due to acute gasping for breath", "breathing"),
    ("audible loud wheezing with distinctly bluish lips and fingernails", "breathing"),
    ("sister's arm went completely limp and she cannot lift it off the table", "confusion_and_stroke"),
    ("throwing up continuously for 6 hours, cannot keep a single sip of water down", "dka_vomiting_high_glucose"),
    ("musalsal ulti pe ulti aa rahi hai, ghoont bhi wapas nikal jata hai", "dka_vomiting_high_glucose"),
    ("دادی اماں صبح سے بے سدھ پڑی ہیں اور آنکھیں نہیں کھول رہیں", "loss_of_consciousness"),
    ("والد صاحب کا سیدھا ہاتھ کام نہیں کر رہا اور آواز لڑکھڑا گئی ہے", "confusion_and_stroke"),
    ("امی جان کہتی ہیں ہوا اندر نہیں جاتی اور سانس بالکل اکھڑی ہوئی ہے", "breathing"),
    ("سینے کے بیچ میں شدید دباؤ ہے اور ساتھ متلی کی کیفیت ہے", "chest_pain"),
    ("پچھلے پانچ گھنٹوں سے مسلسل قے ہو رہی ہے، ایک قطرہ پانی نہیں ٹھہر رہا", "dka_vomiting_high_glucose"),
]

UNSEEN_20_NEGATIVES = [
    "sirf ek dafa subah ulti aayi thi, uske baad se pani aur soup aaram se pee raha hoon",
    "yesterday morning I vomited once after breakfast, keeping fluids down normally today",
    "aik baar ulti hui thi dopehar me, ab theek hoon shikanjabeen pee li hai",
    "had mild nausea after taking metformin, but no vomiting and eating regular dinner",
    "mild pain in left foot toe for the past three weeks, walking fine",
    "dono pairon me saalon se halki jalan rehti hai, sugar ki purani takleef hai",
    "halka sa sar dard hai dopahar se, panadol lene ke baad behtar hai",
    "walked three miles fast, breathed heavily during exercise, completely back to normal after sitting",
    "last year had an episode of dizziness when standing up quickly, never happened again",
    "bachpan mein ek baar behosh hua tha dhoop mein, ab bilkul koi masla nahi hai",
    "chest muscle is slightly sore when I press with my finger where I lifted weights",
    "seene par chot lagne se neel par gaya hai, dabane se dard hota hai",
    "no shortness of breath, breathing is normal, blood pressure is 125/82",
    "denies any chest pain, palpitation, or tightness, feeling calm",
    "face and speech are completely fine, arm strength is strong on both sides",
    "chakkar aya tha do din pehle, pani peene ke baad foran theek ho gaya tha",
    "دل میں اداسی ہے پرانے دوستوں کی یاد آ رہی ہے",
    "کوئی سینے کا درد نہیں، سانس بالکل معمول کے مطابق ہے",
    "ایک دفعہ قے ہوئی تھی، اب ٹھیک ہوں اور چائے پی رہا ہوں",
    "پانچ سال پہلے چکر آئے تھے، اب شوگر 110 ہے اور طبیعت بالکل ٹھیک ہے",
]

@pytest.mark.parametrize("text,expected_category", UNSEEN_20_POSITIVES)
def test_f3d_unseen_positives(text: str, expected_category: str):
    hit, cat = match(text)
    assert hit is True, f"Unseen positive missed: '{text}'"
    assert cat == expected_category, f"Wrong category for '{text}': expected {expected_category}, got {cat}"


@pytest.mark.parametrize("text", UNSEEN_20_NEGATIVES)
def test_f3d_unseen_negatives(text: str):
    hit, cat = match(text)
    assert hit is False, f"Unseen negative falsely flagged as '{cat}': '{text}'"
