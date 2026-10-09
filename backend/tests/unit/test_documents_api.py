import uuid

PDF = ("deed.pdf", b"%PDF-1.4 fake", "application/pdf")


def upload(client, file=PDF, doc_type="deed", **extra):
    return client.post("/documents", files={"file": file}, data={"doc_type": doc_type, **extra})


def test_upload_success(client, storage):
    r = upload(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "uploaded"
    assert body["doc_type"] == "deed"
    assert body["original_filename"] == "deed.pdf"
    assert body["file_key"] == f"{body['id']}/deed.pdf"
    assert storage.objects[body["file_key"]] == (b"%PDF-1.4 fake", "application/pdf")


def test_upload_strips_path_from_filename(client):
    r = upload(client, file=("../../etc/passwd.pdf", b"x", "application/pdf"))
    assert r.status_code == 201
    assert r.json()["file_key"] == f"{r.json()['id']}/passwd.pdf"


def test_wrong_type_415(client, storage):
    r = upload(client, file=("a.txt", b"hello", "text/plain"))
    assert r.status_code == 415
    assert storage.objects == {}


def test_too_large_413(client, storage):
    big = b"0" * (10 * 1024 * 1024 + 1)
    r = upload(client, file=("big.pdf", big, "application/pdf"))
    assert r.status_code == 413
    assert storage.objects == {}


def test_unknown_land_404(client):
    assert upload(client, land_id=str(uuid.uuid4())).status_code == 404


def test_list_returns_uploaded_newest_first(client):
    first = upload(client).json()
    second = upload(client).json()
    ids = [d["id"] for d in client.get("/documents").json()]
    assert ids.index(second["id"]) < ids.index(first["id"])


def test_get_one_and_unknown_404(client):
    doc = upload(client).json()
    assert client.get(f"/documents/{doc['id']}").json()["id"] == doc["id"]
    assert client.get(f"/documents/{uuid.uuid4()}").status_code == 404
