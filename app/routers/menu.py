from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.menu import MenuItem
from app.services.menu_parser import parse_json, parse_pdf

router = APIRouter(prefix="/menu")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def menu_list(request: Request, db: Session = Depends(get_db)):
    items = db.query(MenuItem).order_by(MenuItem.category, MenuItem.name_ar).all()
    categories = sorted({i.category for i in items if i.category})
    return templates.TemplateResponse(request, "menu/list.html", context={
        "items": items,
        "categories": categories,
    })


@router.post("/upload")
async def upload_menu(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    filename = file.filename or ""

    if filename.endswith(".pdf"):
        items_data = parse_pdf(content)
    elif filename.endswith(".json"):
        items_data = parse_json(content)
    else:
        raise HTTPException(status_code=400, detail="Only PDF and JSON files are supported")

    added = 0
    for item_data in items_data:
        if not item_data.get("name_ar"):
            continue
        item = MenuItem(
            name_ar=item_data["name_ar"],
            name_en=item_data.get("name_en", ""),
            description_ar=item_data.get("description_ar", ""),
            description_en=item_data.get("description_en", ""),
            price=float(item_data.get("price", 0) or 0),
            category=item_data.get("category", ""),
            is_active=True,
        )
        db.add(item)
        added += 1

    db.commit()
    return RedirectResponse(url=f"/menu?uploaded={added}", status_code=303)


@router.post("/items")
def add_item(
    name_ar: str = Form(...),
    name_en: str = Form(""),
    description_ar: str = Form(""),
    description_en: str = Form(""),
    price: float = Form(0.0),
    category: str = Form(""),
    db: Session = Depends(get_db),
):
    item = MenuItem(
        name_ar=name_ar,
        name_en=name_en,
        description_ar=description_ar,
        description_en=description_en,
        price=price,
        category=category,
        is_active=True,
    )
    db.add(item)
    db.commit()
    return RedirectResponse(url="/menu", status_code=303)


@router.post("/items/{item_id}/toggle")
def toggle_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.is_active = not item.is_active
    db.commit()
    return RedirectResponse(url="/menu", status_code=303)


@router.post("/items/{item_id}/delete")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/menu", status_code=303)
