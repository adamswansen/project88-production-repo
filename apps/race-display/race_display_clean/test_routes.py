import app; with app.app.test_client() as client: resp = client.get("/display"); print("Status:", resp.status_code); print("Data:", resp.data.decode()[:200])
