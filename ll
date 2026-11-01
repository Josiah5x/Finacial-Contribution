python3 manage.py startapp core
python3 manage.py startapp accounts
python3 manage.py startapp members
python3 manage.py startapp agents
python3 manage.py startapp contributions
python3 manage.py startapp collectionss
python3 manage.py startapp wallets
python3 manage.py startapp withdrawals
python3 manage.py startapp expenses
python3 manage.py startapp reports
python3 manage.py startapp notifications

mkdir -p templates/{accounts,dashboard,members,agents,contributions,collections,wallets,withdrawals,expenses,reports} && touch templates/base.html

mkdir -p static/{css,js,images} media && touch manage.py requirements.txt




    <div class="sidebar-menu">

        <div class="menu-label">Main Menu</div>

        <a href="{% url 'accounts:dashboard' %}"
           class="sidebar-link {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}">
            <i class="bi bi-grid"></i>
            Dashboard
        </a>

        <div class="menu-label">Management</div>

        <a href="{% url 'accounts:user_list' %}" class="sidebar-link">
            <i class="bi bi-people"></i>
            Users
        </a>

        <a href="#" class="sidebar-link">
            <i class="bi bi-person-vcard"></i>
            Members
        </a>

        <a href="#" class="sidebar-link">
            <i class="bi bi-person-badge"></i>
            Collection Agents
        </a>

        <div class="menu-label">Contributions</div>

        <a href="#" class="sidebar-link">
            <i class="bi bi-calendar-check"></i>
            Contribution Plans
        </a>

        <a href="#" class="sidebar-link">
            <i class="bi bi-cash-stack"></i>
            Daily Collections
        </a>

        <a href="#" class="sidebar-link">
            <i class="bi bi-wallet"></i>
            Member Wallets
        </a>

        <a href="#" class="sidebar-link">
            <i class="bi bi-box-arrow-down"></i>
            Withdrawals
        </a>

        <div class="menu-label">Finance</div>

        <a href="#" class="sidebar-link">
            <i class="bi bi-arrow-left-right"></i>
            Transactions
        </a>

        <a href="#" class="sidebar-link">
            <i class="bi bi-receipt"></i>
            Expenses
        </a>

        <a href="#" class="sidebar-link">
            <i class="bi bi-graph-up-arrow"></i>
            Reports
        </a>

        <div class="menu-label">System</div>

        <a href="{% url 'accounts:change_password' %}" class="sidebar-link">
            <i class="bi bi-shield-lock"></i>
            Change Password
        </a>

    </div>
