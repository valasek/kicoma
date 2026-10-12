"""Sample data for the public demo, one coherent set per language.

Every list screen shows at most 10 records. The CS and EN sets have the same
structure, only texts and the currency differ.
"""

from datetime import timedelta
from decimal import Decimal

from django.utils import formats, timezone

from kicoma.kitchen import unit_change
from kicoma.kitchen.models import (
    VAT,
    Allergen,
    AppSettings,
    Article,
    DailyMenu,
    DailyMenuRecipe,
    MealGroup,
    MealType,
    Menu,
    MenuRecipe,
    Recipe,
    RecipeArticle,
    StockIssue,
    StockIssueArticle,
    StockReceipt,
    StockReceiptArticle,
)
from kicoma.kitchen.permissions import Roles

CURRENCY = {"cs": "Kč", "en": "€"}
# Prices below are in CZK; other currencies are converted at this rate.
CZK_PER_UNIT = {"cs": Decimal(1), "en": Decimal(25)}


def _price(czk, language):
    return (Decimal(czk) / CZK_PER_UNIT[language]).quantize(Decimal("0.01"))


VATS = {
    "standard": (21, {"cs": "Základní sazba DPH", "en": "Standard VAT rate"}),
    "reduced": (12, {"cs": "Snížená sazba DPH", "en": "Reduced VAT rate"}),
}

ALLERGENS = (
    ("01", "OBILOVINY OBSAHUJÍCÍ LEPEK", "CEREALS CONTAINING GLUTEN"),
    (
        "01a",
        "OBILOVINY OBSAHUJÍCÍ LEPEK - pšenice",
        "CEREALS CONTAINING GLUTEN - wheat",
    ),
    ("01b", "OBILOVINY OBSAHUJÍCÍ LEPEK - žito", "CEREALS CONTAINING GLUTEN - rye"),
    (
        "01c",
        "OBILOVINY OBSAHUJÍCÍ LEPEK - ječmen",
        "CEREALS CONTAINING GLUTEN - barley",
    ),
    ("01d", "OBILOVINY OBSAHUJÍCÍ LEPEK - oves", "CEREALS CONTAINING GLUTEN - oats"),
    ("01e", "OBILOVINY OBSAHUJÍCÍ LEPEK - špalda", "CEREALS CONTAINING GLUTEN - spelt"),
    ("01f", "OBILOVINY OBSAHUJÍCÍ LEPEK - kamut", "CEREALS CONTAINING GLUTEN - kamut"),
    (
        "01g",
        "OBILOVINY OBSAHUJÍCÍ LEPEK - hybridní odrůdy a výrobky z nich",
        "CEREALS CONTAINING GLUTEN - hybridised strains and products thereof",
    ),
    ("02", "KORÝŠI a výrobky z nich", "CRUSTACEANS and products thereof"),
    ("03", "VEJCE a výrobky z nich", "EGGS and products thereof"),
    ("04", "RYBY a výrobky z nich", "FISH and products thereof"),
    (
        "05",
        "JÁDRA PODZEMNICE OLEJNÉ (ARAŠÍDY) a výrobky z nich",
        "PEANUTS and products thereof",
    ),
    ("06", "SÓJOVÉ BOBY (SÓJA) a výrobky z nich", "SOYBEANS and products thereof"),
    (
        "07",
        "MLÉKO a výrobky z něj (včetně laktózy)",
        "MILK and products thereof (including lactose)",
    ),
    ("08", "SKOŘÁPKOVÉ PLODY", "NUTS"),
    ("08a", "SKOŘÁPKOVÉ PLODY - mandle", "NUTS - almonds"),
    ("08b", "SKOŘÁPKOVÉ PLODY - lískové ořechy", "NUTS - hazelnuts"),
    ("08c", "SKOŘÁPKOVÉ PLODY - vlašské ořechy", "NUTS - walnuts"),
    ("08d", "SKOŘÁPKOVÉ PLODY - kešu ořechy", "NUTS - cashews"),
    ("08e", "SKOŘÁPKOVÉ PLODY - pekanové ořechy", "NUTS - pecan nuts"),
    ("08f", "SKOŘÁPKOVÉ PLODY - para ořechy", "NUTS - Brazil nuts"),
    ("08g", "SKOŘÁPKOVÉ PLODY - pistácie", "NUTS - pistachio nuts"),
    (
        "08h",
        "SKOŘÁPKOVÉ PLODY - makadamie a výrobky z nich",
        "NUTS - macadamia nuts and products thereof",
    ),
    ("09", "CELER a výrobky z něj", "CELERY and products thereof"),
    ("10", "HOŘČICE a výrobky z ní", "MUSTARD and products thereof"),
    (
        "11",
        "SEZAMOVÁ SEMENA (SEZAM) a výrobky z nich",
        "SESAME SEEDS and products thereof",
    ),
    (
        "12",
        "OXID SIŘIČITÝ A SIŘIČITANY v koncentracích vyšších než 10 mg/kg nebo 10 mg/l, "
        "vyjádřeno jako celkový SO2",
        "SULPHUR DIOXIDE AND SULPHITES at concentrations of more than 10 mg/kg "
        "or 10 mg/litre in terms of total SO2",
    ),
    ("13", "VLČÍ BOB (LUPINA) a výrobky z něj", "LUPIN and products thereof"),
    ("14", "MĚKKÝŠI a výrobky z nich", "MOLLUSCS and products thereof"),
)

MEAL_TYPES = {
    "breakfast": {"cs": "Snídaně", "en": "Breakfast"},
    "lunch": {"cs": "Oběd", "en": "Lunch"},
    "snack": {"cs": "Svačina", "en": "Snack"},
    "dinner": {"cs": "Večeře", "en": "Dinner"},
}

MEAL_GROUPS = {
    "residents": {"cs": "Klienti", "en": "Residents"},
    "staff": {"cs": "Zaměstnanci", "en": "Staff"},
    "visitors": {"cs": "Návštěvy", "en": "Visitors"},
}

# key: (names, unit, on stock, min on stock, unit price with VAT, allergen codes,
#       nutrition per 100 g (ml): energy kJ, fat, saturated fat, carbohydrates,
#       sugars, fiber, protein; piece weight)
# Celery is stocked in pieces here and changed to kg by a logged unit change.
ARTICLES = {
    "potatoes": (
        {"cs": "Brambory", "en": "Potatoes"},
        "kg",
        "40",
        "10",
        "18",
        (),
        (322, "0.1", "0", "17", "0.8", "2.2", "2"),
        None,
    ),
    "milk": (
        {"cs": "Mléko polotučné", "en": "Semi-skimmed milk"},
        "l",
        "20",
        "5",
        "24",
        ("07",),
        (199, "1.5", "1", "4.8", "4.8", "0", "3.3"),
        None,
    ),
    "eggs": (
        {"cs": "Vejce", "en": "Eggs"},
        "ks",
        "120",
        "30",
        "4.5",
        ("03",),
        (600, "9.5", "3.1", "0.7", "0.7", "0", "12.6"),
        ("60", "g"),
    ),
    "flour": (
        {"cs": "Mouka hladká", "en": "Plain flour"},
        "kg",
        "25",
        "5",
        "14",
        ("01", "01a"),
        (1450, "1", "0.2", "74", "0.7", "3", "10"),
        None,
    ),
    "butter": (
        {"cs": "Máslo", "en": "Butter"},
        "kg",
        "3",
        "2",
        "220",
        ("07",),
        (3060, "82", "54", "0.6", "0.6", "0", "0.7"),
        None,
    ),
    "chicken": (
        {"cs": "Kuřecí prsa", "en": "Chicken breast"},
        "kg",
        "8",
        "5",
        "160",
        (),
        (460, "1.5", "0.4", "0", "0", "0", "23"),
        None,
    ),
    "rice": (
        {"cs": "Rýže dlouhozrnná", "en": "Long-grain rice"},
        "kg",
        "15",
        "4",
        "35",
        (),
        (1500, "0.7", "0.2", "78", "0.1", "1.3", "7"),
        None,
    ),
    "carrots": (
        {"cs": "Mrkev", "en": "Carrots"},
        "kg",
        "1.5",
        "5",
        "16",
        (),
        (170, "0.2", "0", "7.6", "4.7", "2.8", "0.9"),
        None,
    ),
    "celery": (
        {"cs": "Celer bulva", "en": "Celeriac"},
        "ks",
        "5",
        "3",
        "24",
        ("09",),
        (120, "0.3", "0.1", "2.3", "1.6", "4.2", "1.5"),
        ("800", "g"),
    ),
    "apples": (
        {"cs": "Jablka", "en": "Apples"},
        "kg",
        "0",
        "10",
        "0",
        (),
        (220, "0.2", "0", "12", "10", "2.4", "0.3"),
        None,
    ),
}

NUTRITION = (
    "energy",
    "fat",
    "saturated_fat",
    "carbohydrates",
    "sugars",
    "fiber",
    "protein",
)

CELERY_CHANGE = (
    "celery",
    "kg",
    Decimal("0.8"),
    {
        "cs": "Průměrná bulva celeru váží 0,8 kg (vážení 10 kusů).",
        "en": "An average celeriac weighs 0.8 kg (10 pieces weighed).",
    },
)

# key: (names, portions, procedure, [(article, amount, unit)])
RECIPES = {
    "mashed_potatoes": (
        {"cs": "Bramborová kaše", "en": "Mashed potatoes"},
        10,
        {
            "cs": "Brambory oloupeme, uvaříme v osolené vodě a slijeme. Rozmačkáme "
            "s teplým mlékem a máslem.",
            "en": "Peel the potatoes, boil them in salted water and drain. Mash with "
            "warm milk and butter.",
        },
        [("potatoes", "2", "kg"), ("milk", "300", "ml"), ("butter", "100", "g")],
    ),
    "butter_chicken": (
        {"cs": "Kuřecí prsa na másle", "en": "Butter-fried chicken breast"},
        10,
        {
            "cs": "Prsa nakrájíme na plátky, osolíme a opečeme na másle dozlatova.",
            "en": "Slice the breasts, season with salt and fry in butter until golden.",
        },
        [("chicken", "1.5", "kg"), ("butter", "80", "g")],
    ),
    "steamed_rice": (
        {"cs": "Dušená rýže", "en": "Steamed rice"},
        10,
        {
            "cs": "Rýži propláchneme, zalijeme dvojnásobkem vody a dusíme 18 minut. "
            "Nakonec přidáme máslo.",
            "en": "Rinse the rice, add twice the amount of water and simmer for 18 "
            "minutes. Stir in the butter.",
        },
        [("rice", "800", "g"), ("butter", "30", "g")],
    ),
    "carrot_salad": (
        {"cs": "Mrkvový salát s jablky", "en": "Carrot and apple salad"},
        10,
        {
            "cs": "Mrkev a jablka nastrouháme najemno a promícháme.",
            "en": "Finely grate the carrots and apples and mix.",
        },
        [("carrots", "1", "kg"), ("apples", "400", "g")],
    ),
    "pancakes": (
        {"cs": "Palačinky", "en": "Pancakes"},
        10,
        {
            "cs": "Mouku, mléko a vejce prošleháme na hladké těsto a smažíme tenké "
            "palačinky.",
            "en": "Whisk flour, milk and eggs into a smooth batter and fry thin "
            "pancakes.",
        },
        [("flour", "500", "g"), ("milk", "1", "l"), ("eggs", "4", "ks")],
    ),
    "scrambled_eggs": (
        {"cs": "Míchaná vejce", "en": "Scrambled eggs"},
        10,
        {
            "cs": "Vejce rozšleháme s mlékem a za stálého míchání zvolna srazíme na "
            "másle.",
            "en": "Beat the eggs with milk and cook slowly in butter, stirring "
            "constantly.",
        },
        [("eggs", "20", "ks"), ("butter", "60", "g"), ("milk", "200", "ml")],
    ),
    "celery_soup": (
        {"cs": "Celerová polévka", "en": "Celeriac soup"},
        10,
        {
            "cs": "Celer a brambory nakrájíme, uvaříme doměkka, rozmixujeme a "
            "zjemníme mlékem a máslem.",
            "en": "Dice the celeriac and potatoes, cook until soft, blend and finish "
            "with milk and butter.",
        },
        [
            ("celery", "1", "ks"),
            ("potatoes", "500", "g"),
            ("butter", "50", "g"),
            ("milk", "300", "ml"),
        ],
    ),
    "apple_pie": (
        {"cs": "Jablečný koláč", "en": "Apple pie"},
        10,
        {
            "cs": "Z mouky, másla a vajec vypracujeme těsto, poklademe jablky a "
            "pečeme 35 minut na 180 °C.",
            "en": "Make a dough from flour, butter and eggs, top with apples and bake "
            "for 35 minutes at 180 °C.",
        },
        [
            ("flour", "400", "g"),
            ("butter", "150", "g"),
            ("eggs", "2", "ks"),
            ("apples", "1", "kg"),
        ],
    ),
    "chicken_risotto": (
        {"cs": "Kuřecí rizoto", "en": "Chicken risotto"},
        10,
        {
            "cs": "Maso a zeleninu nakrájíme na kostičky a orestujeme, přidáme rýži, "
            "podlijeme vodou a dusíme doměkka.",
            "en": "Dice the meat and vegetables and sauté, add the rice, pour in "
            "water and simmer until tender.",
        },
        [
            ("chicken", "1", "kg"),
            ("rice", "600", "g"),
            ("carrots", "300", "g"),
            ("celery", "0.25", "ks"),
        ],
    ),
}

# key: (names, meal type, [(recipe, portions)])
MENUS = {
    "breakfast_eggs": (
        {"cs": "Snídaně – míchaná vejce", "en": "Breakfast – scrambled eggs"},
        "breakfast",
        [("scrambled_eggs", 10)],
    ),
    "lunch_chicken": (
        {"cs": "Oběd – kuře s rýží", "en": "Lunch – chicken with rice"},
        "lunch",
        [("celery_soup", 10), ("butter_chicken", 10), ("steamed_rice", 10)],
    ),
    "lunch_risotto": (
        {"cs": "Oběd – rizoto", "en": "Lunch – risotto"},
        "lunch",
        [("celery_soup", 10), ("chicken_risotto", 10), ("carrot_salad", 10)],
    ),
    "snack_pie": (
        {"cs": "Svačina – jablečný koláč", "en": "Snack – apple pie"},
        "snack",
        [("apple_pie", 10)],
    ),
    "dinner_pancakes": (
        {"cs": "Večeře – palačinky", "en": "Dinner – pancakes"},
        "dinner",
        [("pancakes", 10)],
    ),
    "dinner_mash": (
        {"cs": "Večeře – kuře s kaší", "en": "Dinner – chicken with mash"},
        "dinner",
        [("butter_chicken", 10), ("mashed_potatoes", 10)],
    ),
}

# (days from today, meal group, menu, portions of every recipe)
DAILY_MENUS = (
    (-1, "residents", "lunch_chicken", 25),
    (-1, "staff", "lunch_chicken", 12),
    (0, "residents", "breakfast_eggs", 25),
    (0, "residents", "lunch_risotto", 25),
    (0, "staff", "lunch_risotto", 12),
    (0, "residents", "dinner_pancakes", 25),
    (1, "residents", "breakfast_eggs", 25),
    (1, "residents", "lunch_chicken", 25),
    (1, "visitors", "lunch_chicken", 8),
    (1, "residents", "snack_pie", 25),
)

# (days from today created, days from today approved or None, comment,
#  [(article, amount, unit, unit price without VAT, VAT)])
STOCK_RECEIPTS = (
    (
        -10,
        -9,
        {
            "cs": "Velkoobchod – zelenina a maso",
            "en": "Wholesaler – vegetables and meat",
        },
        [
            ("potatoes", "50", "kg", "16.07", "reduced"),
            ("chicken", "10", "kg", "142.86", "reduced"),
            ("rice", "20", "kg", "31.25", "reduced"),
            ("carrots", "10", "kg", "14.29", "reduced"),
            ("celery", "6", "ks", "21.43", "reduced"),
        ],
    ),
    (
        -5,
        -5,
        {"cs": "Mlékárna a pekárna", "en": "Dairy and bakery supplier"},
        [
            ("milk", "30", "l", "21.43", "reduced"),
            ("butter", "5", "kg", "196.43", "reduced"),
            ("eggs", "180", "ks", "4.02", "reduced"),
            ("flour", "25", "kg", "12.5", "reduced"),
        ],
    ),
    (
        0,
        None,
        {"cs": "Objednávka – docházející zboží", "en": "Order – items running low"},
        [
            ("apples", "20", "kg", "26.79", "reduced"),
            ("carrots", "10", "kg", "14.29", "reduced"),
        ],
    ),
)

MANUAL_STOCK_ISSUE = (
    {"cs": "Pečení na oslavu narozenin", "en": "Baking for a birthday party"},
    [("flour", "1", "kg"), ("eggs", "6", "ks"), ("butter", "0.25", "kg")],
)


def load(language, users):
    """Create the demo data for `language`; `users` maps Roles to demo users."""
    today = timezone.localdate()
    AppSettings.objects.create(currency=CURRENCY[language])
    vats = {
        key: VAT.objects.create(percentage=percentage, rate=names[language])
        for key, (percentage, names) in VATS.items()
    }
    allergens = {
        code: Allergen.objects.create(
            code=code, description=cs if language == "cs" else en
        )
        for code, cs, en in ALLERGENS
    }
    meal_types = {
        key: MealType.objects.create(meal_type=names[language])
        for key, names in MEAL_TYPES.items()
    }
    meal_groups = {
        key: MealGroup.objects.create(meal_group=names[language])
        for key, names in MEAL_GROUPS.items()
    }
    articles = _create_articles(language, allergens)
    recipes = _create_recipes(language, articles)
    _create_stock_receipts(language, users, articles, vats, today)
    _apply_unit_change(language, users, articles)
    menus = _create_menus(language, meal_types, recipes)
    daily_menus = _create_daily_menus(meal_groups, menus, today)
    _create_stock_issues(language, users, articles, daily_menus, today)


def _create_articles(language, allergens):
    articles = {}
    for key, (
        names,
        unit,
        on_stock,
        minimum,
        price,
        codes,
        nutrition,
        piece,
    ) in ARTICLES.items():
        article = Article.objects.create(
            article=names[language],
            unit=unit,
            on_stock=Decimal(on_stock),
            min_on_stock=Decimal(minimum),
            total_price=Decimal(on_stock) * _price(price, language),
            piece_weight=Decimal(piece[0]) if piece else None,
            piece_weight_unit=piece[1] if piece else None,
            **{name: Decimal(value) for name, value in zip(NUTRITION, nutrition)},
        )
        article.allergen.set([allergens[code] for code in codes])
        articles[key] = article
    return articles


def _create_recipes(language, articles):
    recipes = {}
    for key, (names, portions, procedure, lines) in RECIPES.items():
        recipe = Recipe.objects.create(
            recipe=names[language], norm_amount=portions, procedure=procedure[language]
        )
        for article, amount, unit in lines:
            RecipeArticle.objects.create(
                recipe=recipe,
                article=articles[article],
                amount=Decimal(amount),
                unit=unit,
            )
        recipes[key] = recipe
    return recipes


def _create_stock_receipts(language, users, articles, vats, today):
    for created, approved, comment, lines in STOCK_RECEIPTS:
        receipt = StockReceipt.objects.create(
            date_created=today + timedelta(days=created),
            user_created=users[Roles.STOCKKEEPER],
            comment=comment[language],
        )
        if approved is not None:
            receipt.approved = True
            receipt.date_approved = today + timedelta(days=approved)
            receipt.user_approved = users[Roles.STOCKKEEPER]
            receipt.save()
        for article, amount, unit, price, vat in lines:
            StockReceiptArticle.objects.create(
                stock_receipt=receipt,
                article=articles[article],
                amount=Decimal(amount),
                unit=unit,
                price_without_vat=_price(price, language),
                vat=vats[vat],
            )
        _backdate(StockReceipt, receipt, created)


def _apply_unit_change(language, users, articles):
    key, new_unit, factor, note = CELERY_CHANGE
    article = Article.objects.get(pk=articles[key].pk)
    preview = unit_change.preview_article_change(
        article, new_unit, factor, note[language]
    )
    unit_change.apply_article_change(
        article.pk,
        new_unit,
        factor,
        note[language],
        users[Roles.STOCKKEEPER],
        preview.fingerprint,
        confirmed=True,
    )
    articles[key].refresh_from_db()


def _create_menus(language, meal_types, recipes):
    menus = {}
    for key, (names, meal_type, lines) in MENUS.items():
        menu = Menu.objects.create(
            menu=names[language], meal_type=meal_types[meal_type]
        )
        for recipe, portions in lines:
            MenuRecipe.objects.create(
                menu=menu, recipe=recipes[recipe], amount=portions
            )
        menus[key] = menu
    return menus


def _create_daily_menus(meal_groups, menus, today):
    daily_menus = []
    for days, meal_group, menu_key, portions in DAILY_MENUS:
        menu = menus[menu_key]
        daily_menu = DailyMenu.objects.create(
            date=today + timedelta(days=days),
            menu=menu,
            meal_group=meal_groups[meal_group],
            meal_type=menu.meal_type,
        )
        for menu_recipe in menu.menurecipe.all():
            DailyMenuRecipe.objects.create(
                daily_menu=daily_menu, recipe=menu_recipe.recipe, amount=portions
            )
        daily_menus.append(daily_menu)
    return daily_menus


def _create_stock_issues(language, users, articles, daily_menus, today):
    for days, approved in ((-1, True), (0, False)):
        date = today + timedelta(days=days)
        StockIssue.create_from_daily_menu(
            [menu for menu in daily_menus if menu.date == date],
            formats.date_format(date, "SHORT_DATE_FORMAT"),
            users[Roles.COOK],
            menu_date=date,
        )
        issue = StockIssue.objects.latest("pk")
        if approved:
            issue.approved = True
            issue.date_approved = date
            issue.user_approved = users[Roles.STOCKKEEPER]
            issue.save()
        _backdate(StockIssue, issue, days)
    comment, lines = MANUAL_STOCK_ISSUE
    issue = StockIssue.objects.create(
        user_created=users[Roles.COOK], comment=comment[language]
    )
    for article, amount, unit in lines:
        StockIssueArticle.objects.create(
            stock_issue=issue,
            article=articles[article],
            amount=Decimal(amount),
            unit=unit,
            average_unit_price=articles[article].average_price,
        )


def _backdate(model, instance, days):
    if days:
        stamp = instance.created + timedelta(days=days)
        model.objects.filter(pk=instance.pk).update(created=stamp, modified=stamp)
