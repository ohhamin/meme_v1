import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:intl/intl.dart';

import '../services/api_client.dart';


class DailyMarkdownScreen extends StatefulWidget {
  const DailyMarkdownScreen({
    super.key,
    required this.kind,
  });

  final String kind;

  @override
  State<DailyMarkdownScreen> createState() => _DailyMarkdownScreenState();
}


class _DailyMarkdownScreenState extends State<DailyMarkdownScreen> {
  DateTime _selected = DateTime.now();
  late Future<String> _future;

  String get _label => widget.kind == 'news' ? '뉴스' : '판단';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = ApiClient.instance.getDailyMarkdown(widget.kind, _selected);
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final first = DateTime(now.year, now.month, now.day)
        .subtract(const Duration(days: 6));

    final picked = await showDatePicker(
      context: context,
      initialDate: _selected,
      firstDate: first,
      lastDate: now,
    );

    if (picked != null) {
      setState(() {
        _selected = picked;
        _load();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final dateText = DateFormat('yyyy-MM-dd').format(_selected);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
          child: SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: _pickDate,
              icon: const Icon(Icons.calendar_month),
              label: Text(dateText),
            ),
          ),
        ),
        Expanded(
          child: FutureBuilder<String>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Center(
                  child: Text(dateText + ' ' + _label + ' 데이터가 없습니다.'),
                );
              }
              return Markdown(
                data: snapshot.data ?? '',
                padding: const EdgeInsets.all(16),
              );
            },
          ),
        ),
      ],
    );
  }
}
