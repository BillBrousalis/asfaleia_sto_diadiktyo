<?php
/**
 * Cadmus Lab A — "Αναφορά απάτης" button in the Roundcube toolbar.
 * Sends the subject of the selected message to the lab server, which answers whether
 * it was a scam, and shows the feedback (and the consequences) in a dialog.
 * Reported scams are moved to the folder "Αναφορές". Nothing else leaves the server.
 */
class cadmus_report extends rcube_plugin
{
    public $task = 'mail';
    private const API = 'http://127.0.0.1:8080/api/report';
    private const STATE_API = 'http://127.0.0.1:8080/api/plugin_state';
    private const RESTORE_DONE = 'http://127.0.0.1:8080/api/restore_done';
    // the start screen and progress page of this lab (one name-based vhost on the shared lab server)
    private const HOME = 'http://phishing.labs.example/home';
    private const PROGRESS = 'http://phishing.labs.example/progress';
    private $lab_state = null;
    private const FOLDER = 'Αναφορές';

    public function init()
    {
        $this->register_action('plugin.cadmus_report', [$this, 'report']);
        $this->include_script('outcome.js');
        $this->include_script('cadmus_report.js');
        $this->include_stylesheet('cadmus_report.css');
        $this->add_texts('localization/', true);
        $this->add_hook('storage_connected', [$this, 'on_connected']);
        $this->add_hook('render_page', [$this, 'on_render']);
        $this->add_button([
            'command'    => 'plugin.cadmus_report',
            'type'       => 'link',
            'label'      => 'cadmus_report.button',
            'title'      => 'cadmus_report.title',
            'class'      => 'button cadmus-report disabled',
            'classact'   => 'button cadmus-report',
            'innerclass' => 'inner',
        ], 'toolbar');
    }

    /** State of the exercise, asked once per request: should the mails be restored, must the player restart? */
    private function lab_state()
    {
        if ($this->lab_state === null) {
            $ctx = stream_context_create(['http' => ['method' => 'GET', 'timeout' => 2, 'ignore_errors' => true]]);
            $raw = @file_get_contents(self::STATE_API, false, $ctx);
            $data = $raw ? json_decode($raw, true) : null;
            $this->lab_state = is_array($data) ? $data : [];
        }
        return $this->lab_state;
    }

    /** After a reset, the reported mails go back to the inbox, unread. */
    public function on_connected($args)
    {
        $st = $this->lab_state();
        if (!empty($st['restore'])) {
            $rc = rcmail::get_instance();
            $folder = rcube_charset::convert(self::FOLDER, RCUBE_CHARSET, 'UTF7-IMAP');
            if ($rc->storage->folder_exists($folder)) {
                $uids = $rc->storage->search_once($folder, 'ALL')->get();
                if ($uids) {
                    $rc->storage->move_message($uids, 'INBOX', $folder);
                }
            }
            $rc->storage->set_flag('*', 'UNSEEN', 'INBOX');
            $ctx = stream_context_create(['http' => ['method' => 'POST', 'timeout' => 2, 'ignore_errors' => true, 'content' => '']]);
            @file_get_contents(self::RESTORE_DONE, false, $ctx);
            $this->lab_state['restore'] = false;
        }
        return $args;
    }

    /** Tells the page where the progress page is, and whether the player has to go there now. */
    public function on_render($args)
    {
        $st = $this->lab_state();
        $out = rcmail::get_instance()->output;
        $out->set_env('cadmus_progress', self::PROGRESS);
        $out->set_env('cadmus_home', self::HOME);
        $out->set_env('cadmus_redirect', !empty($st['restart']));
        return $args;
    }

    public function report()
    {
        $rc   = rcmail::get_instance();
        $uid  = rcube_utils::get_input_value('_uid', rcube_utils::INPUT_POST);
        $mbox = rcube_utils::get_input_value('_mbox', rcube_utils::INPUT_POST);

        $headers = $rc->storage->get_message_headers($uid, $mbox);
        $subject = $headers ? trim(rcube_mime::decode_header((string) $headers->subject, $headers->charset)) : '';
        $answer  = $subject !== '' ? $this->ask($subject) : null;

        if (!$answer) {
            $rc->output->command('plugin.cadmus_report_result', ['error' => true]);
            $rc->output->send();
            return;
        }

        $moved = false;
        if ($answer['ok']) {
            $folder = rcube_charset::convert(self::FOLDER, RCUBE_CHARSET, 'UTF7-IMAP');
            if (!$rc->storage->folder_exists($folder)) {
                $rc->storage->create_folder($folder, true);
            }
            $moved = $rc->storage->move_message($uid, $folder, $mbox);
        }
        $answer['moved'] = $moved;
        $answer['uid']   = $uid;
        $rc->output->command('plugin.cadmus_report_result', $answer);
        $rc->output->send();
    }

    private function ask($subject)
    {
        $ctx = stream_context_create(['http' => [
            'method'  => 'POST',
            'header'  => "Content-Type: application/json\r\n",
            'content' => json_encode(['subject' => $subject], JSON_UNESCAPED_UNICODE),
            'timeout' => 5,
            'ignore_errors' => true,
        ]]);
        $raw = @file_get_contents(self::API, false, $ctx);
        $data = $raw ? json_decode($raw, true) : null;
        return is_array($data) && isset($data['id']) ? $data : null;
    }
}
