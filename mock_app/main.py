"""
Mock Legacy Banking / Member-Servicing Application (CoreBank Servicing Terminal v4.2).
Simulates a legacy back-office financial servicing app.
Intentionally avoids test-ids to mimic legacy enterprise systems.
"""

import time
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse

app = FastAPI(title="CoreBank Servicing Terminal")

BASE_CSS = """
<style>
    body { font-family: "Courier New", Courier, monospace; background-color: #1a1a1a; color: #33ff33; margin: 0; padding: 20px; }
    .container { max-width: 900px; margin: 0 auto; background: #000; border: 3px double #33ff33; padding: 20px; box-shadow: 0 0 15px rgba(51,255,51,0.3); }
    .header { text-align: center; border-bottom: 2px solid #33ff33; padding-bottom: 10px; margin-bottom: 20px; }
    .header h1 { margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px; }
    .header p { margin: 5px 0 0 0; font-size: 12px; color: #88ff88; }
    .nav-bar { background: #111; padding: 8px; border: 1px solid #33ff33; margin-bottom: 20px; }
    .nav-bar a { color: #ffff33; text-decoration: none; font-weight: bold; margin-right: 15px; }
    .nav-bar a:hover { text-decoration: underline; background: #33ff33; color: #000; }
    fieldset { border: 1px solid #33ff33; margin-bottom: 20px; padding: 15px; }
    legend { color: #ffff33; font-weight: bold; padding: 0 5px; }
    label { display: inline-block; width: 180px; font-weight: bold; }
    input[type="text"], input[type="number"], select { background: #111; color: #33ff33; border: 1px solid #33ff33; padding: 6px; font-family: monospace; width: 250px; }
    input[type="submit"], button, .btn { background: #33ff33; color: #000; border: none; padding: 8px 16px; font-weight: bold; font-family: monospace; cursor: pointer; text-decoration: none; display: inline-block; }
    input[type="submit"]:hover, button:hover, .btn:hover { background: #ffff33; color: #000; }
    .data-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    .data-table th, .data-table td { border: 1px solid #33ff33; padding: 8px; text-align: left; }
    .data-table th { background: #113311; color: #ffff33; }
    .banner { padding: 12px; margin-bottom: 20px; border: 1px solid; font-weight: bold; }
    .banner-error { background: #330000; color: #ff5555; border-color: #ff5555; }
    .banner-warning { background: #333300; color: #ffff55; border-color: #ffff55; }
    .banner-success { background: #003300; color: #55ff55; border-color: #55ff55; }
    .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center; }
    .modal-content { background: #111; border: 2px solid #ffff33; padding: 25px; max-width: 500px; text-align: center; color: #ffff33; }
    .modal-content button { margin-top: 15px; }
</style>
"""

def render_page(title: str, body_content: str, dialog: bool = False) -> HTMLResponse:
    modal_html = ""
    if dialog:
        modal_html = """
        <div class="modal-overlay" id="system-dialog">
            <div class="modal-content">
                <h3>*** SYSTEM NOTICE ***</h3>
                <p>Scheduled Maintenance Window begins at 24:00 EST. Please finish active servicing sessions.</p>
                <button onclick="document.getElementById('system-dialog').style.display='none'">DISMISS ANNOUNCEMENT</button>
            </div>
        </div>
        """
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - CoreBank Terminal v4.2</title>
    {BASE_CSS}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>COREBANK FINANCIAL SERVICING TERMINAL</h1>
            <p>SYSTEM ID: CBS-PROD-EAST-04 | OPERATOR: AGENT_SYSTEM_USER</p>
        </div>
        <div class="nav-bar">
            <a href="/">[MEMBER SEARCH]</a>
            <a href="/members/12345">[DEMO MEMBER 12345]</a>
            <a href="/members/99999">[DEMO NOT FOUND]</a>
            <a href="/members/77777">[DEMO RESTRICTED]</a>
        </div>
        {body_content}
        {modal_html}
    </div>
</body>
</html>
"""
    return HTMLResponse(content=full_html)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, delay: int = 0, dialog: bool = False):
    if delay > 0:
        time.sleep(delay)
    content = """
    <fieldset>
        <legend>MEMBER SEARCH PROTOCOL</legend>
        <form action="/search" method="POST">
            <p>Enter 5-digit Member Identifier to access customer records:</p>
            <p>
                <label for="member_id_input">MEMBER ID NUM:</label>
                <input type="text" id="member_id_input" name="member_id" placeholder="e.g. 12345" required autocomplete="off" />
            </p>
            <p>
                <input type="submit" value="EXECUTE SEARCH PROTOCOL" />
            </p>
        </form>
    </fieldset>
    """
    return render_page("Member Search Protocol", content, dialog=dialog)


@app.post("/search", response_class=HTMLResponse)
async def search_member(member_id: str = Form(...)):
    member_id = member_id.strip()
    if not member_id.isdigit():
        content = f"""
        <div class="banner banner-error">
            VALIDATION_ERROR: Member ID format invalid. Must be numeric digits (e.g. 12345). Observed: '{member_id}'
        </div>
        <a href="/" class="btn">&laquo; RETURN TO SEARCH</a>
        """
        return render_page("Validation Error", content)
    
    if member_id == "99999":
        content = f"""
        <div class="banner banner-error">
            MEMBER_NOT_FOUND: Member ID {member_id} could not be located in CoreBank Database.
        </div>
        <a href="/" class="btn">&laquo; RETURN TO SEARCH</a>
        """
        return render_page("Member Not Found", content)
    
    if member_id == "77777":
        content = f"""
        <div class="banner banner-error">
            PERMISSION_DENIED: Access level insufficient to view restricted financial record {member_id}.
        </div>
        <a href="/" class="btn">&laquo; RETURN TO SEARCH</a>
        """
        return render_page("Permission Denied", content)
        
    return HTMLResponse(headers={"Location": f"/members/{member_id}"}, status_code=303)


@app.get("/members/{member_id}", response_class=HTMLResponse)
async def member_details(member_id: str, delay: int = Query(0), dialog: bool = Query(False)):
    if delay > 0:
        time.sleep(delay)

    if member_id == "99999":
        content = f"""
        <div class="banner banner-error">
            MEMBER_NOT_FOUND: Member ID {member_id} could not be located in CoreBank Database.
        </div>
        <a href="/" class="btn">&laquo; RETURN TO SEARCH</a>
        """
        return render_page("Member Not Found", content, dialog=dialog)

    if member_id == "77777":
        content = f"""
        <div class="banner banner-error">
            PERMISSION_DENIED: Access level insufficient to view restricted account {member_id}.
        </div>
        <a href="/" class="btn">&laquo; RETURN TO SEARCH</a>
        """
        return render_page("Permission Denied", content, dialog=dialog)

    content = f"""
    <div class="banner banner-success">
        STATUS: ACCOUNT RECORD ACTIVE | MEMBER ID: {member_id}
    </div>

    <fieldset>
        <legend>MEMBER PROFILE SUMMARY</legend>
        <p><strong>PRIMARY HOLDER:</strong> Jane Doe</p>
        <p><strong>SSN / TAX ID:</strong> ***-**-6789</p>
        <p><strong>MEMBER SINCE:</strong> 2018-04-12</p>
        <p><strong>RISK RATING:</strong> LOW</p>
    </fieldset>

    <fieldset>
        <legend>ACCOUNT BALANCES & DEPOSITS</legend>
        <table class="data-table">
            <thead>
                <tr>
                    <th>ACCOUNT TYPE</th>
                    <th>ACCOUNT NUMBER</th>
                    <th>STATUS</th>
                    <th>CURRENT BALANCE</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>SAVINGS ACCOUNT</td>
                    <td>SAV-12345-01</td>
                    <td>ACTIVE</td>
                    <td><span id="savings-balance">$12,450.00</span></td>
                </tr>
                <tr>
                    <td>CHECKING ACCOUNT</td>
                    <td>CHK-12345-02</td>
                    <td>ACTIVE</td>
                    <td><span id="checking-balance">$3,120.50</span></td>
                </tr>
            </tbody>
        </table>
    </fieldset>

    <div style="margin-top: 20px;">
        <a href="/members/{member_id}/new-subaccount" class="btn">OPEN NEW SUB-ACCOUNT FORM</a>
        <a href="/" class="btn" style="background:#555; color:#fff;">BACK TO SEARCH</a>
    </div>
    """
    return render_page(f"Member Details {member_id}", content, dialog=dialog)


@app.get("/members/{member_id}/new-subaccount", response_class=HTMLResponse)
async def new_subaccount_form(member_id: str):
    content = f"""
    <fieldset>
        <legend>SUB-ACCOUNT CREATION FORM - MEMBER {member_id}</legend>
        <form action="/members/{member_id}/new-subaccount/review" method="POST">
            <p>
                <label for="subaccount_type">ACCOUNT TYPE:</label>
                <select id="subaccount_type" name="account_type">
                    <option value="MONEY_MARKET">Money Market Savings</option>
                    <option value="HIGH_YIELD">High Yield Deposit</option>
                    <option value="CHRISTMAS_CLUB">Holiday Savings Club</option>
                </select>
            </p>
            <p>
                <label for="initial_deposit">INITIAL DEPOSIT ($):</label>
                <input type="number" id="initial_deposit" name="initial_deposit" value="500.00" min="50" step="10" required />
            </p>
            <p>
                <label for="account_nickname">ACCOUNT NICKNAME:</label>
                <input type="text" id="account_nickname" name="nickname" placeholder="e.g. Emergency Fund" required />
            </p>
            <p>
                <input type="submit" value="REVIEW SUB-ACCOUNT CREATION" />
                <a href="/members/{member_id}" class="btn" style="background:#555; color:#fff;">CANCEL</a>
            </p>
        </form>
    </fieldset>
    """
    return render_page(f"Create Sub-Account - Member {member_id}", content)


@app.post("/members/{member_id}/new-subaccount/review", response_class=HTMLResponse)
async def subaccount_review(
    member_id: str,
    account_type: str = Form(...),
    initial_deposit: str = Form(...),
    nickname: str = Form(...)
):
    content = f"""
    <div class="banner banner-warning">
        PRE-COMMITMENT REVIEW: Confirmation Required Before Record Update
    </div>

    <fieldset>
        <legend>SUB-ACCOUNT PROPOSED SPECIFICATIONS</legend>
        <p><strong>MEMBER ID:</strong> {member_id}</p>
        <p><strong>TARGET PRODUCT:</strong> {account_type}</p>
        <p><strong>OPENING DEPOSIT:</strong> ${initial_deposit}</p>
        <p><strong>NICKNAME:</strong> {nickname}</p>
        <p><strong>STATUS:</strong> AWAITING OPERATOR CONFIRMATION</p>
    </fieldset>

    <div class="banner banner-success" id="confirmation-screen-header">
        CONFIRMATION STAGE REACHED: No funds have been transferred yet.
    </div>

    <div style="margin-top: 20px;">
        <a href="/members/{member_id}" class="btn" id="finish-btn">FINISH SERVICING WORKFLOW</a>
    </div>
    """
    return render_page(f"Sub-Account Confirmation - Member {member_id}", content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_app.main:app", host="0.0.0.0", port=8000, reload=True)
