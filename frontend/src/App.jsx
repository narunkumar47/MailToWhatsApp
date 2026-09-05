import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "";
function App() {
  const [activePage, setActivePage] = useState("dashboard");

  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [email, setEmail] = useState("");
  const [emails, setEmails] = useState([]);

  const [userId, setUserId] = useState(null);

  const [gmailConnected, setGmailConnected] = useState(false);
  const [monitoringEnabled, setMonitoringEnabled] = useState(false);

  const [stats, setStats] = useState({
    emails_sent: 0,
    processed_emails: 0,
    last_checked_at: null
  });

  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState("info");

  const [loading, setLoading] = useState(false);
  const [loadingEmails, setLoadingEmails] = useState(false);

  const [previewMessage, setPreviewMessage] = useState("");

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const showStatus = (message, type = "info") => {
    setStatus(message);
    setStatusType(type);

    setTimeout(() => {
      setStatus("");
    }, 4500);
  };

  const loadUser = async (id) => {
    try {
      const response = await fetch(
        `${API_URL}/users/${id}`
      );

      const data = await response.json();

      if (response.ok && !data.error) {
        setEmail(data.email || "");
        setWhatsappNumber(data.whatsapp_number || "");
        setMonitoringEnabled(
          Boolean(data.monitoring_enabled)
        );
        setGmailConnected(Boolean(data.gmail_connected ?? true));

        setStats((current) => ({
          ...current,
          emails_sent: data.emails_sent_count || 0,
          last_checked_at: data.last_checked_at || null
        }));
      }
    } catch (error) {
      console.error(error);
    }
  };

  const loadStats = async (id = userId) => {
    if (!id) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/users/${id}/stats`
      );

      const data = await response.json();

      if (!response.ok || data.error) {
        return;
      }

      setStats({
        emails_sent: data.emails_sent || 0,
        processed_emails: data.processed_emails || 0,
        last_checked_at: data.last_checked_at || null
      });
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(
      window.location.search
    );

    const returnedEmail = params.get("email");
    const returnedUserId = params.get("user_id");
    const gmailConnectedParam =
      params.get("gmail_connected");
    const error = params.get("error");

    if (gmailConnectedParam === "true") {
      if (returnedEmail) {
        setEmail(returnedEmail);
        localStorage.setItem(
          "mailtowhatsapp_email",
          returnedEmail
        );
      }

      if (returnedUserId) {
        const id = Number(returnedUserId);

        setUserId(id);

        localStorage.setItem(
          "mailtowhatsapp_user_id",
          String(id)
        );

        loadUser(id);
        loadStats(id);
        loadEmails(id);
      }

      showStatus(
        "Gmail connected successfully.",
        "success"
      );

      window.history.replaceState(
        {},
        document.title,
        window.location.pathname
      );
    }

    if (error) {
      showStatus(
        "We couldn't connect Gmail. Please try again.",
        "error"
      );

      window.history.replaceState(
        {},
        document.title,
        window.location.pathname
      );
    }

    const savedEmail =
      localStorage.getItem(
        "mailtowhatsapp_email"
      );

    const savedNumber =
      localStorage.getItem(
        "mailtowhatsapp_whatsapp"
      );

    const savedUserId =
      localStorage.getItem(
        "mailtowhatsapp_user_id"
      );

    if (savedEmail && !returnedEmail) {
      setEmail(savedEmail);
    }

    if (savedNumber) {
      setWhatsappNumber(savedNumber);
    }

    if (savedUserId && !returnedUserId) {
      const id = Number(savedUserId);

      setUserId(id);
      loadUser(id);
      loadStats(id);
      loadEmails(id);
    }
  }, []);

  useEffect(() => {
    if (!userId) {
      return undefined;
    }

    const interval = setInterval(() => {
      loadStats(userId);
    }, 15000);

    return () => clearInterval(interval);
  }, [userId]);

  const connectGmail = () => {
    window.location.href =
      `${API_URL}/auth/login`;
  };

  const saveWhatsApp = async () => {
    if (!userId) {
      showStatus(
        "Connect Gmail first.",
        "error"
      );
      return;
    }

    const cleanedNumber =
      whatsappNumber.replace(/\D/g, "");

    if (!cleanedNumber) {
      showStatus(
        "Enter your WhatsApp number.",
        "error"
      );
      return;
    }

    if (cleanedNumber.length < 10) {
      showStatus(
        "Please enter a valid WhatsApp number.",
        "error"
      );
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/users/whatsapp?user_id=${userId}&whatsapp_number=${encodeURIComponent(
          cleanedNumber
        )}`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error ||
          "Could not save WhatsApp number."
        );
      }

      setWhatsappNumber(cleanedNumber);

      localStorage.setItem(
        "mailtowhatsapp_whatsapp",
        cleanedNumber
      );

      showStatus(
        "WhatsApp number saved.",
        "success"
      );
    } catch (error) {
      showStatus(
        error.message,
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const toggleMonitoring = async (enabled) => {
    if (!userId) {
      showStatus(
        "Connect Gmail first.",
        "error"
      );
      return;
    }

    if (enabled && !whatsappNumber) {
      showStatus(
        "Add your WhatsApp number first.",
        "error"
      );

      navigate("connections");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/users/${userId}/monitoring?enabled=${enabled}`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error ||
          "Could not update automation."
        );
      }

      setMonitoringEnabled(enabled);

      await loadStats(userId);

      showStatus(
        enabled
          ? "Automation is now active."
          : "Automation has been paused.",
        "success"
      );
    } catch (error) {
      showStatus(
        error.message,
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const loadEmails = async (id = userId) => {
    if (!id) {
      showStatus(
        "Connect Gmail first.",
        "error"
      );
      return;
    }

    setLoadingEmails(true);

    try {
      const response = await fetch(
        `${API_URL}/emails?user_id=${id}`
      );

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error ||
          "Could not load emails."
        );
      }

      setEmails(data.emails || []);

      showStatus(
        `${data.count || 0} useful emails found.`,
        "success"
      );
    } catch (error) {
      showStatus(
        error.message,
        "error"
      );
    } finally {
      setLoadingEmails(false);
    }
  };

  const loadPreview = async () => {
    if (!userId) {
      showStatus(
        "Connect Gmail first.",
        "error"
      );
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/emails/whatsapp-preview?user_id=${userId}`
      );

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(
          data.error ||
          "Could not create preview."
        );
      }

      setPreviewMessage(
        data.whatsapp_message || ""
      );

      showStatus(
        "Preview created.",
        "success"
      );
    } catch (error) {
      showStatus(
        error.message,
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const sendToWhatsApp = async () => {
    if (!userId) {
      showStatus(
        "Connect Gmail first.",
        "error"
      );
      return;
    }

    if (!whatsappNumber) {
      showStatus(
        "Add your WhatsApp number first.",
        "error"
      );
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/emails/send-to-whatsapp?user_id=${userId}`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      await loadStats(userId);
      await loadEmails(userId);

      showStatus(
        data.sent_count > 0
          ? `${data.sent_count} email(s) sent to WhatsApp.`
          : "No new emails to send.",
        "success"
      );
    } catch (error) {
      showStatus(
        error.message,
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const navigate = (page) => {
    setActivePage(page);
    setMobileMenuOpen(false);
  };

  const setupSteps = [
    {
      title: "Connect Gmail",
      description: "Link your inbox",
      done: gmailConnected
    },
    {
      title: "Add WhatsApp",
      description: "Choose where to send",
      done: Boolean(whatsappNumber)
    },
    {
      title: "Start automation",
      description: "Turn forwarding on",
      done: monitoringEnabled
    }
  ];

  const completedSteps =
    setupSteps.filter(
      (step) => step.done
    ).length;

  const formatDate = (dateString) => {
    if (!dateString) return "";

    try {
      const date = new Date(dateString);

      if (Number.isNaN(date.getTime())) {
        return dateString;
      }

      return date.toLocaleDateString(
        undefined,
        {
          day: "numeric",
          month: "short"
        }
      );
    } catch {
      return dateString;
    }
  };

  const formatDateTime = (dateString) => {
    if (!dateString) {
      return "Not checked yet";
    }

    try {
      const date = new Date(dateString);

      if (Number.isNaN(date.getTime())) {
        return dateString;
      }

      return date.toLocaleString(
        undefined,
        {
          day: "numeric",
          month: "short",
          hour: "numeric",
          minute: "2-digit"
        }
      );
    } catch {
      return dateString;
    }
  };

  const liveStatStyle = {
    flex: "1",
    minWidth: "180px",
    padding: "18px 20px",
    border: "1px solid #e9edf5",
    borderRadius: "16px",
    background: "#ffffff"
  };

  const renderDashboard = () => (
    <div className="page-content">

      <div className="welcome-banner">

        <div className="welcome-copy">

          <div className="eyebrow light">
            YOUR EMAIL ASSISTANT
          </div>

          <h1>
            {email
              ? "Welcome back."
              : "Welcome to MailToWhatsApp."}
          </h1>

          <p>
            Important emails in your inbox,
            delivered where you'll actually see them.
          </p>

          {!monitoringEnabled && (
            <button
              className="banner-button"
              onClick={() =>
                navigate(
                  gmailConnected && whatsappNumber
                    ? "automation"
                    : "connections"
                )
              }
            >
              {gmailConnected && whatsappNumber
                ? "Turn on automation"
                : "Finish setup"}
              <span>→</span>
            </button>
          )}

        </div>

        <div className="banner-graphic">

          <div className="graphic-orbit orbit-one" />
          <div className="graphic-orbit orbit-two" />

          <div className="graphic-card email-graphic">
            <span>✉</span>
          </div>

          <div className="graphic-arrow">
            →
          </div>

          <div className="graphic-card whatsapp-graphic">
            <span>W</span>
          </div>

        </div>

      </div>

      <div className="section-heading">
        <div>
          <h2>
            Your setup
          </h2>

          <p>
            Everything you need to keep your inbox connected.
          </p>
        </div>
      </div>

      <div className="stats-grid">

        <StatusCard
          icon="G"
          title="Gmail"
          value={
            gmailConnected
              ? "Connected"
              : "Connect Gmail"
          }
          detail={
            gmailConnected
              ? email
              : "Your inbox is waiting"
          }
          connected={gmailConnected}
          onClick={() =>
            navigate("connections")
          }
        />

        <StatusCard
          icon="W"
          title="WhatsApp"
          value={
            whatsappNumber
              ? "Ready"
              : "Set up WhatsApp"
          }
          detail={
            whatsappNumber
              ? `+${whatsappNumber}`
              : "Choose your delivery number"
          }
          connected={Boolean(whatsappNumber)}
          onClick={() =>
            navigate("connections")
          }
        />

        <StatusCard
          icon="↗"
          title="Automation"
          value={
            monitoringEnabled
              ? "Running"
              : "Paused"
          }
          detail={
            monitoringEnabled
              ? "Checking every 5 minutes"
              : "Turn it on when you're ready"
          }
          connected={monitoringEnabled}
          onClick={() =>
            navigate("automation")
          }
        />

      </div>

      <section className="content-card" style={{ marginBottom: "22px" }}>
        <div className="card-header">
          <div>
            <h2>Live activity</h2>
            <p>Your current MailToWhatsApp activity, updated automatically.</p>
          </div>

          <button
            className="link-button"
            onClick={() => {
              loadStats();
              loadEmails();
            }}
          >
            Refresh
            <span>↻</span>
          </button>
        </div>

        <div
          style={{
            display: "flex",
            gap: "14px",
            flexWrap: "wrap"
          }}
        >
          <div style={liveStatStyle}>
            <span className="small-label">SENT TO WHATSAPP</span>
            <strong style={{ display: "block", fontSize: "28px", marginTop: "8px" }}>
              {stats.emails_sent}
            </strong>
            <span style={{ color: "#667085", fontSize: "13px" }}>
              Successfully delivered
            </span>
          </div>

          <div style={liveStatStyle}>
            <span className="small-label">PROCESSED EMAILS</span>
            <strong style={{ display: "block", fontSize: "28px", marginTop: "8px" }}>
              {stats.processed_emails}
            </strong>
            <span style={{ color: "#667085", fontSize: "13px" }}>
              Protected from duplicates
            </span>
          </div>

          <div style={liveStatStyle}>
            <span className="small-label">LAST CHECK</span>
            <strong style={{ display: "block", fontSize: "18px", marginTop: "12px" }}>
              {formatDateTime(stats.last_checked_at)}
            </strong>
            <span style={{ color: "#667085", fontSize: "13px" }}>
              Gmail monitoring activity
            </span>
          </div>
        </div>
      </section>

      <div className="dashboard-grid">

        <section className="content-card">

          <div className="card-header">
            <div>
              <h2>
                Useful emails
              </h2>

              <p>
                Important messages detected from your inbox.
              </p>
            </div>

            <button
              className="link-button"
              onClick={() => {
                navigate("emails");
                loadEmails();
              }}
            >
              View all
              <span>→</span>
            </button>
          </div>

          {emails.length > 0 ? (

            <div className="email-list">

              {emails
                .slice(0, 5)
                .map((item) => (
                  <EmailRow
                    key={item.id}
                    email={item}
                    formatDate={formatDate}
                  />
                ))}

            </div>

          ) : (

            <div className="dashboard-empty">

              <div className="empty-illustration">
                <div>✉</div>
              </div>

              <h3>
                Your inbox is ready
              </h3>

              <p>
                Check Gmail and we'll find the messages that actually matter.
              </p>

              <button
                className="primary-button"
                onClick={loadEmails}
                disabled={loadingEmails}
              >
                {loadingEmails
                  ? "Checking inbox..."
                  : "Check my inbox"}
              </button>

            </div>

          )}

        </section>

        <section className="content-card">

          <div className="card-header">
            <div>
              <h2>
                Quick actions
              </h2>

              <p>
                Manage MailToWhatsApp in seconds.
              </p>
            </div>
          </div>

          <div className="quick-actions">

            <QuickAction
              icon="↔"
              title="Connections"
              description="Gmail & WhatsApp"
              onClick={() =>
                navigate("connections")
              }
            />

            <QuickAction
              icon="↗"
              title="Automation"
              description={
                monitoringEnabled
                  ? "Currently running"
                  : "Currently paused"
              }
              onClick={() =>
                navigate("automation")
              }
            />

            <QuickAction
              icon="✉"
              title="Email activity"
              description="View useful emails"
              onClick={() => {
                navigate("emails");
                loadEmails();
              }}
            />

            <QuickAction
              icon="◷"
              title="WhatsApp preview"
              description="See a sample message"
              onClick={() =>
                navigate("activity")
              }
            />

          </div>

        </section>

      </div>

    </div>
  );

  const renderConnections = () => (
    <div className="page-content">

      <PageTitle
        eyebrow="CONNECTIONS"
        title="Connect your accounts"
        description="Connect Gmail and choose the WhatsApp number where your important emails should arrive."
      />

      <div className="connection-list">

        <section className="connection-card">

          <div className="connection-brand gmail-brand">
            G
          </div>

          <div className="connection-main">

            <div className="connection-title-row">

              <div>
                <h2>
                  Gmail
                </h2>

                <p className="connection-subtitle">
                  Your email inbox
                </p>
              </div>

              <ConnectionBadge
                connected={gmailConnected}
              />

            </div>

            <p className="connection-description">
              MailToWhatsApp checks your inbox for useful messages while filtering out promotions, newsletters and security codes.
            </p>

            {gmailConnected && (
              <div className="connected-account">
                <div className="mini-avatar">
                  {email
                    ? email.charAt(0).toUpperCase()
                    : "G"}
                </div>

                <div>
                  <strong>
                    {email}
                  </strong>

                  <span>
                    Gmail connected
                  </span>
                </div>
              </div>
            )}

          </div>

          <div className="connection-action">

            <button
              className={
                gmailConnected
                  ? "secondary-button"
                  : "primary-button"
              }
              onClick={connectGmail}
            >
              {gmailConnected
                ? "Reconnect"
                : "Connect Gmail"}
            </button>

          </div>

        </section>

        <section className="connection-card">

          <div className="connection-brand whatsapp-brand">
            W
          </div>

          <div className="connection-main">

            <div className="connection-title-row">

              <div>
                <h2>
                  WhatsApp
                </h2>

                <p className="connection-subtitle">
                  Your delivery destination
                </p>
              </div>

              <ConnectionBadge
                connected={Boolean(
                  whatsappNumber
                )}
              />

            </div>

            <p className="connection-description">
              Important emails will be formatted into simple WhatsApp messages and sent to this number.
            </p>

            <div className="phone-field">

              <label>
                WhatsApp number
              </label>

              <div className="phone-input">

                <span>
                  +
                </span>

                <input
                  value={whatsappNumber}
                  onChange={(event) =>
                    setWhatsappNumber(
                      event.target.value
                    )
                  }
                  placeholder="91 78934 42733"
                />

              </div>

              <small>
                Include your country code. For example, 91 for India.
              </small>

            </div>

          </div>

          <div className="connection-action">

            <button
              className="primary-button"
              onClick={saveWhatsApp}
              disabled={loading}
            >
              {loading
                ? "Saving..."
                : whatsappNumber
                ? "Save changes"
                : "Save number"}
            </button>

          </div>

        </section>

      </div>

      <div className="security-note">

        <div className="security-icon">
          ✓
        </div>

        <div>
          <strong>
            Your accounts stay private
          </strong>

          <p>
            We only use the access required to find and deliver useful emails.
          </p>
        </div>

      </div>

    </div>
  );

  const renderAutomation = () => (
    <div className="page-content">

      <PageTitle
        eyebrow="AUTOMATION"
        title="Email → WhatsApp"
        description="Let MailToWhatsApp handle the repetitive work for you."
      />

      <section
        className={`automation-hero ${
          monitoringEnabled
            ? "automation-active"
            : ""
        }`}
      >

        <div className="automation-status">

          <div
            className={`automation-icon-large ${
              monitoringEnabled
                ? "active"
                : "paused"
            }`}
          >
            {monitoringEnabled
              ? "✓"
              : "Ⅱ"}
          </div>

          <div>

            <span className="small-label">
              STATUS
            </span>

            <h2>
              {monitoringEnabled
                ? "Automation is running"
                : "Automation is paused"}
            </h2>

            <p>
              {monitoringEnabled
                ? "We'll check your inbox every 5 minutes and forward new useful emails."
                : "Turn automation on and MailToWhatsApp will take care of the rest."}
            </p>

          </div>

        </div>

        <button
          className={
            monitoringEnabled
              ? "danger-button"
              : "primary-button large-button"
          }
          onClick={() =>
            toggleMonitoring(
              !monitoringEnabled
            )
          }
          disabled={loading}
        >
          {loading
            ? "Updating..."
            : monitoringEnabled
            ? "Pause automation"
            : "Turn on automation"}
        </button>

      </section>

      <section className="content-card">

        <div className="card-header">
          <div>
            <h2>
              How MailToWhatsApp works
            </h2>

            <p>
              Three simple steps happen in the background.
            </p>
          </div>
        </div>

        <div className="workflow">

          <WorkflowStep
            number="01"
            title="We check your inbox"
            description="New Gmail messages are checked automatically."
          />

          <WorkflowConnector />

          <WorkflowStep
            number="02"
            title="We find what matters"
            description="Promotions and low-value messages are filtered out."
          />

          <WorkflowConnector />

          <WorkflowStep
            number="03"
            title="You get it on WhatsApp"
            description="Useful emails are turned into clean, readable messages."
          />

        </div>

      </section>

      <section className="content-card rules-card">

        <div className="card-header">
          <div>
            <h2>
              What gets through?
            </h2>

            <p>
              Our current filtering rules.
            </p>
          </div>
        </div>

        <div className="rules-grid">

          <Rule
            icon="✓"
            title="Important emails"
            description="Job updates, orders, payments and account changes."
          />

          <Rule
            icon="×"
            title="Promotions"
            description="Sales, discounts, offers and marketing emails stay out."
            muted
          />

          <Rule
            icon="×"
            title="Security codes"
            description="OTP and verification emails aren't forwarded."
            muted
          />

          <Rule
            icon="✓"
            title="Duplicate protection"
            description="The same email won't be sent repeatedly."
          />

        </div>

      </section>

    </div>
  );

  const renderEmails = () => (
    <div className="page-content">

      <div className="page-title-row">

        <PageTitle
          eyebrow="EMAIL ACTIVITY"
          title="Useful emails"
          description="Messages MailToWhatsApp thinks are worth your attention."
        />

        <button
          className="primary-button"
          onClick={loadEmails}
          disabled={loadingEmails}
        >
          {loadingEmails
            ? "Checking..."
            : "Refresh inbox"}
        </button>

      </div>

      <section className="content-card">

        {emails.length > 0 ? (

          <div className="email-list full">

            {emails.map((item) => (
              <EmailRow
                key={item.id}
                email={item}
                formatDate={formatDate}
              />
            ))}

          </div>

        ) : (

          <div className="empty-state">

            <div className="empty-illustration large">
              ✉
            </div>

            <h2>
              No useful emails yet
            </h2>

            <p>
              Check your inbox and we'll show you the messages that matter.
            </p>

            <button
              className="primary-button"
              onClick={loadEmails}
              disabled={loadingEmails}
            >
              {loadingEmails
                ? "Checking inbox..."
                : "Check my inbox"}
            </button>

          </div>

        )}

      </section>

    </div>
  );

  const renderActivity = () => (
    <div className="page-content">

      <PageTitle
        eyebrow="ACTIVITY"
        title="Everything looks clear"
        description="A quick overview of your MailToWhatsApp setup."
      />

      <section className="content-card" style={{ marginBottom: "22px" }}>
        <div className="card-header">
          <div>
            <h2>Delivery status</h2>
            <p>Real-time status for your connected Gmail and WhatsApp flow.</p>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            gap: "14px",
            flexWrap: "wrap"
          }}
        >
          <div style={liveStatStyle}>
            <span className="small-label">SENT</span>
            <strong style={{ display: "block", fontSize: "26px", marginTop: "8px" }}>
              {stats.emails_sent}
            </strong>
          </div>

          <div style={liveStatStyle}>
            <span className="small-label">PROCESSED</span>
            <strong style={{ display: "block", fontSize: "26px", marginTop: "8px" }}>
              {stats.processed_emails}
            </strong>
          </div>

          <div style={liveStatStyle}>
            <span className="small-label">LAST CHECK</span>
            <strong style={{ display: "block", fontSize: "16px", marginTop: "12px" }}>
              {formatDateTime(stats.last_checked_at)}
            </strong>
          </div>
        </div>
      </section>

      <section className="content-card activity-card">

        <ActivityItem
          icon="G"
          title="Gmail"
          description={
            gmailConnected
              ? `Connected as ${email}`
              : "Gmail still needs to be connected."
          }
          status={
            gmailConnected
              ? "Connected"
              : "Needs setup"
          }
          success={gmailConnected}
        />

        <ActivityItem
          icon="W"
          title="WhatsApp"
          description={
            whatsappNumber
              ? `Messages will be delivered to +${whatsappNumber}`
              : "Add a WhatsApp number to receive messages."
          }
          status={
            whatsappNumber
              ? "Ready"
              : "Needs setup"
          }
          success={Boolean(
            whatsappNumber
          )}
        />

        <ActivityItem
          icon="↗"
          title="Automation"
          description={
            monitoringEnabled
              ? "Your inbox is being checked automatically."
              : "Automatic forwarding is currently paused."
          }
          status={
            monitoringEnabled
              ? "Running"
              : "Paused"
          }
          success={monitoringEnabled}
        />

      </section>

      <section className="content-card preview-section">

        <div className="card-header">

          <div>
            <h2>
              WhatsApp preview
            </h2>

            <p>
              See exactly how a useful email will look when delivered.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              gap: "10px",
              flexWrap: "wrap"
            }}
          >
            <button
              className="secondary-button"
              onClick={loadPreview}
              disabled={loading}
            >
              {loading
                ? "Creating..."
                : "Create preview"}
            </button>

            <button
              className="primary-button"
              onClick={sendToWhatsApp}
              disabled={
                loading ||
                !gmailConnected ||
                !whatsappNumber
              }
            >
              {loading
                ? "Sending..."
                : "Send to WhatsApp"}
            </button>
          </div>

        </div>

        {previewMessage ? (

          <div className="preview-container">

            <div className="phone-preview">

              <div className="phone-header">

                <div className="phone-avatar">
                  M
                </div>

                <div>
                  <strong>
                    MailToWhatsApp
                  </strong>

                  <span>
                    online
                  </span>
                </div>

              </div>

              <div className="chat-area">

                <div className="whatsapp-message">
                  {previewMessage}
                </div>

              </div>

            </div>

          </div>

        ) : (

          <div className="preview-placeholder">

            <div>
              ◌
            </div>

            <p>
              Create a preview to see your WhatsApp message.
            </p>

          </div>

        )}

      </section>

    </div>
  );

  const renderSettings = () => (
    <div className="page-content">

      <PageTitle
        eyebrow="SETTINGS"
        title="Account"
        description="Manage your MailToWhatsApp account."
      />

      <section className="content-card settings-card">

        <div className="profile">

          <div className="profile-avatar">
            {email
              ? email.charAt(0).toUpperCase()
              : "A"}
          </div>

          <div>
            <h2>
              {email || "Your account"}
            </h2>

            <p>
              MailToWhatsApp account
            </p>
          </div>

        </div>

        <div className="divider" />

        <SettingRow
          title="Gmail account"
          value={
            email || "Not connected"
          }
          badge={
            gmailConnected
              ? "Connected"
              : "Not connected"
          }
          positive={gmailConnected}
        />

        <SettingRow
          title="WhatsApp number"
          value={
            whatsappNumber
              ? `+${whatsappNumber}`
              : "Not added"
          }
          badge={
            whatsappNumber
              ? "Ready"
              : "Not added"
          }
          positive={Boolean(
            whatsappNumber
          )}
        />

        <SettingRow
          title="Automatic forwarding"
          value={
            monitoringEnabled
              ? "Checking every 5 minutes"
              : "Currently paused"
          }
          badge={
            monitoringEnabled
              ? "Active"
              : "Paused"
          }
          positive={monitoringEnabled}
        />

      </section>

    </div>
  );

  const renderPage = () => {
    switch (activePage) {
      case "connections":
        return renderConnections();

      case "automation":
        return renderAutomation();

      case "emails":
        return renderEmails();

      case "activity":
        return renderActivity();

      case "settings":
        return renderSettings();

      default:
        return renderDashboard();
    }
  };

  return (
    <div className="app-shell">

      {mobileMenuOpen && (
        <div
          className="mobile-overlay"
          onClick={() =>
            setMobileMenuOpen(false)
          }
        />
      )}

      <aside
        className={`sidebar ${
          mobileMenuOpen
            ? "sidebar-open"
            : ""
        }`}
      >

        <div className="brand">

          <div className="brand-mark">
            M
          </div>

          <div className="brand-text">
            <strong>
              MailToWhatsApp
            </strong>

            <span>
              Your inbox, simplified.
            </span>
          </div>

        </div>

        <div className="sidebar-section">

          <span className="sidebar-label">
            MENU
          </span>

          <nav>

            <NavItem
              icon="⌂"
              label="Dashboard"
              active={
                activePage === "dashboard"
              }
              onClick={() =>
                navigate("dashboard")
              }
            />

            <NavItem
              icon="✉"
              label="Emails"
              active={
                activePage === "emails"
              }
              onClick={() =>
                navigate("emails")
              }
            />

            <NavItem
              icon="↔"
              label="Connections"
              active={
                activePage === "connections"
              }
              onClick={() =>
                navigate("connections")
              }
            />

            <NavItem
              icon="↗"
              label="Automation"
              active={
                activePage === "automation"
              }
              onClick={() =>
                navigate("automation")
              }
            />

            <NavItem
              icon="◷"
              label="Activity"
              active={
                activePage === "activity"
              }
              onClick={() =>
                navigate("activity")
              }
            />

          </nav>

        </div>

        <div className="sidebar-bottom">

          <NavItem
            icon="⚙"
            label="Settings"
            active={
              activePage === "settings"
            }
            onClick={() =>
              navigate("settings")
            }
          />

          <div className="sidebar-profile">

            <div className="sidebar-avatar">
              {email
                ? email.charAt(0).toUpperCase()
                : "A"}
            </div>

            <div>
              <strong>
                {email
                  ? email.split("@")[0]
                  : "Your account"}
              </strong>

              <span>
                {email || "Not connected"}
              </span>
            </div>

          </div>

        </div>

      </aside>

      <main className="main">

        <header className="topbar">

          <button
            className="mobile-menu-button"
            onClick={() =>
              setMobileMenuOpen(
                !mobileMenuOpen
              )
            }
          >
            ☰
          </button>

          <div className="breadcrumb">

            <span>
              MailToWhatsApp
            </span>

            <b>
              /
            </b>

            <strong>
              {activePage === "dashboard"
                ? "Dashboard"
                : activePage.charAt(0).toUpperCase() +
                  activePage.slice(1)}
            </strong>

          </div>

          <div className="topbar-right">

            {monitoringEnabled && (
              <div className="running-pill">
                <span />
                Automation running
              </div>
            )}

            <div className="topbar-avatar">
              {email
                ? email.charAt(0).toUpperCase()
                : "A"}
            </div>

          </div>

        </header>

        {status && (
          <div
            className={`global-status ${
              statusType
            }`}
          >
            <span>
              {statusType === "success"
                ? "✓"
                : statusType === "error"
                ? "!"
                : "i"}
            </span>

            {status}
          </div>
        )}

        {renderPage()}

      </main>

    </div>
  );
}


// ============================================================
// COMPONENTS
// ============================================================

function PageTitle({
  eyebrow,
  title,
  description
}) {
  return (
    <div className="page-header">

      <div>
        <div className="eyebrow">
          {eyebrow}
        </div>

        <h1>
          {title}
        </h1>

        <p>
          {description}
        </p>
      </div>

    </div>
  );
}


function NavItem({
  icon,
  label,
  active,
  onClick
}) {
  return (
    <button
      className={`nav-item ${
        active ? "active" : ""
      }`}
      onClick={onClick}
    >
      <span className="nav-icon">
        {icon}
      </span>

      <span>
        {label}
      </span>
    </button>
  );
}


function StatusCard({
  icon,
  title,
  value,
  detail,
  connected,
  onClick
}) {
  return (
    <button
      className="status-card"
      onClick={onClick}
    >

      <div
        className={`status-card-icon ${
          connected
            ? "connected"
            : ""
        }`}
      >
        {icon}
      </div>

      <div className="status-card-content">

        <span className="status-card-title">
          {title}
        </span>

        <strong>
          {value}
        </strong>

        <small>
          {detail}
        </small>

      </div>

      <span
        className={`status-indicator ${
          connected
            ? "connected"
            : ""
        }`}
      />

    </button>
  );
}


function QuickAction({
  icon,
  title,
  description,
  onClick
}) {
  return (
    <button
      className="quick-action"
      onClick={onClick}
    >

      <span className="quick-icon">
        {icon}
      </span>

      <span className="quick-content">

        <strong>
          {title}
        </strong>

        <small>
          {description}
        </small>

      </span>

      <span className="quick-arrow">
        →
      </span>

    </button>
  );
}


function ConnectionBadge({
  connected
}) {
  return (
    <span
      className={`connection-badge ${
        connected
          ? "connected"
          : ""
      }`}
    >
      <span />

      {connected
        ? "Connected"
        : "Not connected"}
    </span>
  );
}


function EmailRow({
  email,
  formatDate
}) {
  const sender =
    email.sender ||
    "Unknown sender";

  const subject =
    email.subject ||
    "No subject";

  const displaySender =
    sender
      .replace(
        /<.*?>/g,
        ""
      )
      .trim();

  return (
    <div className="email-row">

      <div className="email-avatar">
        {displaySender
          .charAt(0)
          .toUpperCase() || "?"}
      </div>

      <div className="email-main">

        <div className="email-top">

          <strong>
            {displaySender}
          </strong>

          <span>
            {formatDate(email.date)}
          </span>

        </div>

        <h3>
          {subject}
        </h3>

        {email.body && (
          <p>
            {email.body.slice(0, 120)}
            {email.body.length > 120
              ? "..."
              : ""}
          </p>
        )}

        <div className="email-tags">

          <span>
            {email.classification_reason ||
              "Useful email"}
          </span>

          {typeof email.importance_score ===
            "number" && (
            <span className="score-tag">
              Importance {email.importance_score}
            </span>
          )}

        </div>

      </div>

      <span className="email-arrow">
        →
      </span>

    </div>
  );
}


function WorkflowStep({
  number,
  title,
  description
}) {
  return (
    <div className="workflow-step">

      <div className="workflow-number">
        {number}
      </div>

      <div>
        <strong>
          {title}
        </strong>

        <p>
          {description}
        </p>
      </div>

    </div>
  );
}


function WorkflowConnector() {
  return (
    <div className="workflow-connector">
      →
    </div>
  );
}


function Rule({
  icon,
  title,
  description,
  muted
}) {
  return (
    <div
      className={`rule ${
        muted ? "muted" : ""
      }`}
    >

      <div className="rule-icon">
        {icon}
      </div>

      <div>
        <strong>
          {title}
        </strong>

        <p>
          {description}
        </p>
      </div>

    </div>
  );
}


function ActivityItem({
  icon,
  title,
  description,
  status,
  success
}) {
  return (
    <div className="activity-item">

      <div
        className={`activity-icon ${
          success ? "success" : ""
        }`}
      >
        {icon}
      </div>

      <div className="activity-content">

        <strong>
          {title}
        </strong>

        <span>
          {description}
        </span>

      </div>

      <span
        className={`activity-status ${
          success ? "success" : ""
        }`}
      >
        {status}
      </span>

    </div>
  );
}


function SettingRow({
  title,
  value,
  badge,
  positive
}) {
  return (
    <div className="setting-row">

      <div>
        <strong>
          {title}
        </strong>

        <span>
          {value}
        </span>
      </div>

      <span
        className={`setting-badge ${
          positive ? "positive" : ""
        }`}
      >
        {badge}
      </span>

    </div>
  );
}


export default App;